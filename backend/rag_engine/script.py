import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.sql import text
from sqlalchemy import select, insert

from backend.database.session import session_manager
from backend.rag_engine.models import QdrantIds
from backend.rag_engine.qdrant import VectorStoreManager
from backend.rag_engine.config import RagConfig
from backend.database.executer import sql_manager

import requests
import json
from loguru import logger



class ScriptVector:
    """
    Класс для анализа структуры БД, генерации описаний полей через LLM
    и сохранения векторных представлений в Qdrant.

    Attributes:
        vector_store_manager (VectorStoreManager): Менеджер векторных хранилищ
        engine (AsyncEngine): Асинхронный движок SQLAlchemy
    """

    def __init__(self, db_session_manager=None, vector_store_manager=None):
        """
        Инициализирует экземпляр ScriptVector.
        """
        self.vector_store_manager = vector_store_manager
        self.db_session_manager = db_session_manager
        self.engine = db_session_manager.engine if db_session_manager else None

    async def get_db_schema(self):
        """
        Асинхронно извлекает схему базы данных: список таблиц и их колонок.

        Returns:
            dict[str, list[str]]: Словарь, где ключ - имя таблицы,
                                  значение - список названий колонок

        Example:
             schema = await script.get_db_schema()
             print(schema)
            {
                'users': ['id', 'email', 'created_at'],
                'orders': ['id', 'user_id', 'total']
            }
        """
        # Получаем список всех таблиц через системный запрос
        async with self.engine.connect() as conn:
            # Для PostgreSQL получаем список таблиц из information_schema
            result = await conn.execute(
                text("""
                     SELECT table_name
                     FROM information_schema.tables
                     WHERE table_schema = 'public'
                     """)
            )
            table_names = [row[0] for row in result.fetchall()]

            schema_info = {}

            for table_name in table_names:
                # Получаем колонки для каждой таблицы
                columns_result = await conn.execute(
                    text("""
                         SELECT column_name
                         FROM information_schema.columns
                         WHERE table_schema = 'public'
                           AND table_name = :table_name
                         ORDER BY ordinal_position
                         """),
                    {"table_name": table_name}
                )

                columns = [row[0] for row in columns_result.fetchall()]
                schema_info[table_name] = columns

            return schema_info

    async def db_describe(self):
        """
        Асинхронно генерирует описания для полей базы данных с помощью LLM.

        Returns:
            dict[str, dict[str, str]] | None: Словарь с описаниями полей
        """
        logger.info('Начинаю описывать')
        schema_info = await self.get_db_schema()
        logger.info(schema_info)
        logger.info('Получаю описания')
        prompt = (f'Твоя задача — сгенерировать описания и степень конфиденциальности для полей базы данных.\n'
                  f'Входные данные (схема БД): {schema_info}\n\n'
                  f'Требования к ответу:\n'
                  f'1. Ответ должен быть ТОЛЬКО валидным JSON-объектом\n'
                  f'2. Никакого дополнительного текста, пояснений, markdown-разметки или обрамления кодом\n'
                  f'3. Структура JSON:\n'
                  f'{{\n'
                  f'  "имя_таблицы_1": {{\n'
                  f'    "имя_поля_1": {{\n'
                  f'      "description": "понятное описание на русском языке",\n'
                  f'      "confidentiality": число_от_1_до_10\n'
                  f'    }},\n'
                  f'    "имя_поля_2": {{\n'
                  f'      "description": "понятное описание на русском языке",\n'
                  f'      "confidentiality": число_от_1_до_10\n'
                  f'    }}\n'
                  f'  }},\n'
                  f'  "имя_таблицы_2": {{\n'
                  f'    "имя_поля_1": {{\n'
                  f'      "description": "понятное описание на русском языке",\n'
                  f'      "confidentiality": число_от_1_до_10\n'
                  f'    }}\n'
                  f'  }}\n'
                  f'}}\n\n'
                  f'Правила генерации описаний:\n'
                  f'- Описания должны быть краткими (2-5 слов)\n'
                  f'- Описывай, какие данные хранятся в поле\n'
                  f'- Используй бизнес-контекст, а не технические термины\n'
                  f'- Для id полей пиши "Уникальный идентификатор записи"\n'
                  f'- Для полей с датами пиши "Дата и время создания/изменения/события"\n'
                  f'- Для внешних ключей указывай, на какую таблицу ссылаются\n\n'
                  f'Правила определения степени конфиденциальности (confidentiality от 1 до 10):\n'
                  f'- 1-2: Публичная информация (можно публиковать открыто)\n'
                  f'  * Примеры: id, даты создания, статусы, справочные значения\n'
                  f'- 3-4: Внутренняя информация (можно показывать внутри компании)\n'
                  f'  * Примеры: названия, описания, категории, технические поля\n'
                  f'- 5-6: Ограниченного доступа (только для авторизованных пользователей)\n'
                  f'  * Примеры: email, username, обезличенная статистика\n'
                  f'- 7-8: Конфиденциальная информация (ограниченный круг сотрудников)\n'
                  f'  * Примеры: персональные данные, финансовые показатели, оценки\n'
                  f'- 9-10: Особо конфиденциальная (только владелец и администраторы)\n'
                  f'  * Примеры: пароли, токены, ключи доступа, медицинские данные\n\n'
                  f'Пример:\n'
                  f'Вход: {{"users": ["id", "username", "email", "password", "created_at", "scopes"]}}\n'
                  f'Ответ: {{\n'
                  f'  "users": {{\n'
                  f'    "id": {{\n'
                  f'      "description": "Уникальный идентификатор пользователя",\n'
                  f'      "confidentiality": 1\n'
                  f'    }},\n'
                  f'    "username": {{\n'
                  f'      "description": "Имя пользователя для входа",\n'
                  f'      "confidentiality": 5\n'
                  f'    }},\n'
                  f'    "email": {{\n'
                  f'      "description": "Электронная почта пользователя",\n'
                  f'      "confidentiality": 6\n'
                  f'    }},\n'
                  f'    "password": {{\n'
                  f'      "description": "Хэш пароля",\n'
                  f'      "confidentiality": 10\n'
                  f'    }},\n'
                  f'    "created_at": {{\n'
                  f'      "description": "Дата регистрации пользователя",\n'
                  f'      "confidentiality": 2\n'
                  f'    }},\n'
                  f'    "scopes": {{\n'
                  f'      "description": "Разрешения и роли пользователя",\n'
                  f'      "confidentiality": 8\n'
                  f'    }}\n'
                  f'  }}\n'
                  f'}}\n\n'
                  f'Начинай генерацию ответа сразу с JSON:')

        url = 'http://10.11.12.64:11434/api/generate'
        data = {
            "model": "qwen2.5:3b",
            "stream": False,
            "prompt": prompt
        }

        try:
            response = requests.post(url, json=data)
            processed_response = response.json()['response']
            return json.loads(processed_response)

        except Exception as e:
            logger.error(f'Ошибка запроса {e}')

    @session_manager.connection(commit=True)
    async def add_data_to_vdb(self, db_session: AsyncSession, collection_name: str, vector_manager: VectorStoreManager,
                              fields_description: dict[str, dict] | None = None):
        """
        Генерирует описания для полей базы данных и сохраняет их в векторную БД.

        Args:
            collection_name: Название коллекции
            db_session: Сессия бд
            vector_database: Список названий векторных хранилищ
            vector_manager: Менеджер векторных хранилищ
            fields_description: Описания полей (если None, генерируются автоматически)

        Returns:
            str | None: Сообщение об ошибке или None при успехе
        """

        logger.info('Начинаю обработку')

        try:
            if fields_description is None:
                response = await self.db_describe()
            else:
                response = fields_description

            logger.info(f'Ответ обработчика бд: {response}, {type(response)}')

            if response is None:
                logger.error("Не удалось получить описания полей")
                return "Ошибка: не удалось получить описания полей"
            logger.info(collection_name)
            vector_store = vector_manager.get_vector_store(collection_name)
            logger.info('векторная бд получена')
            if vector_store is None:
                logger.error(f"Векторное хранилище {collection_name} не найдено")


            for key, value in response.items():
                logger.info(key)
                existing_field = await sql_manager(
                    select(QdrantIds).where(
                        QdrantIds.table_name == key
                    )
                ).scalar_one_or_none(db_session)
                logger.info(existing_field)
                if existing_field:
                    logger.info(f'Таблица {key} уже в векторной бд')
                else:
                    text = f'Название таблицы: {key} Значения и описания: {value}'
                    point = await vector_store.aadd_texts(
                        texts=[text],
                        metadatas=[{
                            'table_name': key,
                            'value': value
                        }]
                    )
                    await sql_manager(
                        insert(QdrantIds).values(
                            {'ids': point[0], 'table_name': key}
                        )
                    ).execute(db_session)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return f'Ошибка {e}'

    @staticmethod
    async def get_all_points(vector_manager: VectorStoreManager):
        try:
            qdr_client = vector_manager.qdr_client
            rag_config = RagConfig()
            all_points = []
            logger.info(rag_config.LIST_COLLECTION)

            for name in rag_config.LIST_COLLECTION:
                logger.info(f"Получение точек из коллекции: {name}")

                # scroll возвращает кортеж (points, next_offset)
                result = qdr_client.scroll(
                    collection_name=name,
                    with_payload=True,
                )

                # Распаковываем кортеж
                points, next_offset = result

                # Обрабатываем полученные точки
                for point in points:
                    point_data = {
                        'id': point.id,
                        'collection': name,
                        'matadata': point.payload['metadata']
                    }

                    all_points.append(point_data)

                logger.info(f"Получено {len(points)} точек из {name}")

                while next_offset is not None:
                    result = qdr_client.scroll(
                        collection_name=name,
                        with_payload=True,
                        offset=next_offset
                    )
                    points, next_offset = result

                    for point in points:
                        point_data = {
                            'id': point.id,
                            'collection': name,
                            'payload': point.payload
                        }
                        if point.payload and 'metadata' in point.payload:
                            point_data['table_info'] = point.payload['metadata']

                        all_points.append(point_data)

                    logger.info(f"Получено еще {len(points)} точек из {name}")

            logger.success(f"Всего получено точек: {len(all_points)}")
            return all_points

        except Exception as e:
            logger.error(f'Ошибка получения точек: {e}')
            logger.exception("Детали ошибки:")
            return []

