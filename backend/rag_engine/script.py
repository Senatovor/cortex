import asyncio
from sqlalchemy import inspect, create_engine

from qdrant import VectorStoreManager
from backend.database.session import DatabaseSessionManager
import requests
import json
from loguru import logger

db_session = DatabaseSessionManager('postgresql+asyncpg://postgres:1111@localhost/service')
asyncio.run(db_session.init())


class ScriptVector:
    """
    Класс для анализа структуры БД, генерации описаний полей через LLM
    и сохранения векторных представлений в Qdrant.

    Attributes:
        vector_store_manager (VectorStoreManager): Менеджер векторных хранилищ
        engine (AsyncEngine): Асинхронный движок SQLAlchemy
        sync_engine (Engine): Синхронный движок SQLAlchemy для инспекции БД
    """

    def __init__(self):
        """
        Инициализирует экземпляр ScriptVector.

        Создает синхронный движок для инспекции БД и получает асинхронный движок
        из глобального менеджера сессий.
        """
        self.vector_store_manager = VectorStoreManager()
        self.engine = db_session.engine
        sync_connection_string = 'postgresql://postgres:1111@localhost/service'
        self.sync_engine = create_engine(sync_connection_string)

    @staticmethod
    def get_db_schema(engine):
        """
        Извлекает схему базы данных: список таблиц и их колонок.

        Args:
            engine: Синхронный движок SQLAlchemy для инспекции БД

        Returns:
            dict[str, list[str]]: Словарь, где ключ - имя таблицы,
                                  значение - список названий колонок

        Example:
             schema = ScriptVector.get_db_schema(sync_engine)
             print(schema)
            {
                'users': ['id', 'email', 'created_at'],
                'orders': ['id', 'user_id', 'total']
            }
        """
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        schema_info = {}

        for table_name in table_names:
            columns = inspector.get_columns(table_name)
            column_names = [col['name'] for col in columns]
            schema_info[table_name] = column_names

        return schema_info

    def db_describe(self):
        """
        Генерирует описания для полей базы данных с помощью LLM.

        Отправляет схему БД в локальную LLM (qwen2.5:3b через Ollama API)
        и получает JSON с описаниями полей на русском языке.

        Returns:
            dict[str, dict[str, str]] | None: Словарь с описаниями полей,
                                              где ключ - имя таблицы,
                                              значение - словарь {поле: описание}
                                              Возвращает None при ошибке

        Raises:
            Exception: При ошибках сетевого запроса или парсинга JSON
                       (логируются через logger.error)

        Example:
             script = ScriptVector()
             descriptions = script.db_describe()
             print(descriptions)
            {
                'users': {
                    'id': 'Уникальный идентификатор пользователя',
                    'email': 'Email пользователя'
                }
            }

        Notes:
            - Требует доступности Ollama API по адресу http://10.11.12.64:11434
            - Модель: qwen2.5:3b
            - Ответ должен быть строго в формате JSON без дополнительного текста
        """
        logger.info('Начинаю описывать')
        schema_info = self.get_db_schema(self.sync_engine)
        prompt = (f'Твоя задача — сгенерировать описания для полей базы данных.'
                  f'Входные данные (схема БД): {schema_info}'

                  f'Требования к ответу:'
                  f'1. Ответ должен быть ТОЛЬКО валидным JSON-объектом'
                  f'2. Никакого дополнительного текста, пояснений, markdown-разметки или обрамления кодом'
                  '3. Структура JSON:'
                  '{'
                  '  "имя_таблицы_1": {'
                  f'    "имя_поля_1": "понятное описание на русском языке",'
                  f'    "имя_поля_2": "понятное описание на русском языке"'
                  '  }'
                  '  "имя_таблицы_2": {'
                  f'    "имя_поля_1": "понятное описание на русском языке"'
                  '  }'
                  '}'

                  f'Правила генерации описаний:'
                  f'- Описания должны быть краткими (2-5 слов)'
                  f'- Описывай, какие данные хранятся в поле'
                  f'- Используй бизнес-контекст, а не технические термины'
                  f'- Для id полей пиши "Уникальный идентификатор записи"'
                  f'- Для полей с датами пиши "Дата и время создания/изменения/события"'
                  f'- Для внешних ключей указывай, на какую таблицу ссылаются'

                  f'Пример:'
                  'Вход: {"users": ["id", "email", "created_at"], "orders": ["id", "user_id", "total"]}'
                  'Ответ: {"users": {"id": "Уникальный идентификатор пользователя", "email": "Email пользователя", "created_at": "Дата регистрации"}, "orders": {"id": "Уникальный идентификатор заказа", "user_id": "ID пользователя, создавшего заказ", "total": "Сумма заказа"}}'

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

    async def add_data_to_vdb(self, vector_database: list[str], vector_manager: VectorStoreManager,
                                fields_description: dict[str, dict] | None = None):
        """
        Генерирует описания для полей базы данных с помощью LLM.

        Отправляет схему БД в локальную LLM (qwen2.5:3b через Ollama API)
        и получает JSON с описаниями полей на русском языке.

        Returns:
            dict[str, dict[str, str]] | None: Словарь с описаниями полей,
                                              где ключ - имя таблицы,
                                              значение - словарь {поле: описание}
                                              Возвращает None при ошибке

        Raises:
            Exception: При ошибках сетевого запроса или парсинга JSON
                       (логируются через logger.error)

        Example:
             script = ScriptVector()
             descriptions = script.db_describe()
             print(descriptions)
            {
                'users': {
                    'id': 'Уникальный идентификатор пользователя',
                    'email': 'Email пользователя'
                }
            }
        """
        logger.info('Начинаю обработку')
        try:
            response = self.db_describe()
            print(type(response))
            logger.info(f'Ответ обработчика бд: {response}')
            for db in vector_database:
                vector_store = vector_manager.get_vector_store(db)
                for key in response.keys():
                    for item, value in response[key].items():
                        print(value, type(value))
                        vector_store.add_texts(
                            texts=[value],
                            metadatas=[{
                                'table_name': key,
                                'field_name': item,
                            }]
                        )
        except Exception as e:
            return f'Ошибка {e}'

script = ScriptVector()
vector_manager = VectorStoreManager()
asyncio.run(vector_manager.init())
asyncio.run(script.add_data_to_vdb(['structure'], vector_manager))
