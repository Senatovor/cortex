import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.sql import text

from backend.rag_engine.qdrant import VectorStoreManager
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
        prompt = (f'Твоя задача — сгенерировать описания для полей базы данных.\n'
                  f'Входные данные (схема БД): {schema_info}\n\n'
                  f'Требования к ответу:\n'
                  f'1. Ответ должен быть ТОЛЬКО валидным JSON-объектом\n'
                  f'2. Никакого дополнительного текста, пояснений, markdown-разметки или обрамления кодом\n'
                  f'3. Структура JSON:\n'
                  f'{{\n'
                  f'  "имя_таблицы_1": {{\n'
                  f'    "имя_поля_1": "понятное описание на русском языке",\n'
                  f'    "имя_поля_2": "понятное описание на русском языке"\n'
                  f'  }},\n'
                  f'  "имя_таблицы_2": {{\n'
                  f'    "имя_поля_1": "понятное описание на русском языке"\n'
                  f'  }}\n'
                  f'}}\n\n'
                  f'Правила генерации описаний:\n'
                  f'- Описания должны быть краткими (2-5 слов)\n'
                  f'- Описывай, какие данные хранятся в поле\n'
                  f'- Используй бизнес-контекст, а не технические термины\n'
                  f'- Для id полей пиши "Уникальный идентификатор записи"\n'
                  f'- Для полей с датами пиши "Дата и время создания/изменения/события"\n'
                  f'- Для внешних ключей указывай, на какую таблицу ссылаются\n\n'
                  f'Пример:\n'
                  f'Вход: {{"users": ["id", "email", "created_at"], "orders": ["id", "user_id", "total"]}}\n'
                  f'Ответ: {{"users": {{"id": "Уникальный идентификатор пользователя", "email": "Email пользователя", "created_at": "Дата регистрации"}}, "orders": {{"id": "Уникальный идентификатор заказа", "user_id": "ID пользователя, создавшего заказ", "total": "Сумма заказа"}}}}\n\n'
                  f'Начинай генерацию ответа сразу с JSON:')

        print(prompt)

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

    async def add_data_to_vdb(self, collection_name: str, vector_manager: VectorStoreManager,
                              fields_description: dict[str, dict] | None = None):
        """
        Генерирует описания для полей базы данных и сохраняет их в векторную БД.

        Args:
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
            logger.info(collection_name)
            vector_store = vector_manager.get_vector_store(collection_name)
            logger.info('векторная бд получена')
            if vector_store is None:
                logger.error(f"Векторное хранилище {collection_name} не найдено")


            for key, value in response.items():
                text = f'Название таблицы: {key} Значения и описания: {value}'
                    # Запускаем синхронный add_texts в отдельном потоке
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: vector_store.add_texts(
                        texts=[text],
                        metadatas=[{
                            'table_name': key,
                            'value': value
                        }]
                    )
                )
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return f'Ошибка {e}'