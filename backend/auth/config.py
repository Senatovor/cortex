from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class AuthConfig(BaseSettings):
    """Класс конфигурации авторизации.

    Загружает настройки из .env файла или переменных окружения.

    Attributes:
        SECRET_KEY(str): Секретный ключ для JWT
        ALGORITHM(str): Алгоритм шифрования JWT
        ACCESS_TOKEN_EXPIRE(int): Время жизни access токена (в минутах)
    """
    # Настройки аутентификации
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE: int
    REFRESH_TOKEN_EXPIRE: int

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )
