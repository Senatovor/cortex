from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class RagConfig(BaseSettings):
    """Класс конфигурации RAG системы.

    Загружает настройки из .env файла или переменных окружения.

    Attributes:

    """
    MODEL_NAME: str
    MODEL_HOST: str
    TEMPERATURE: float

    QDRANT_HOST: str
    QDRANT_PORT: int
    VECTOR_SIZE: int
    LIST_COLLECTION: list[str]

    EMBEDDINGS_MODEL_NAME: str

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )
