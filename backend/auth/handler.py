from argon2.exceptions import VerifyMismatchError, VerificationError
from loguru import logger
from pydantic import SecretStr
from datetime import datetime, timedelta, timezone
from jose import jwt
from argon2 import PasswordHasher

from ..config import config


class AuthHandler:
    """Класс для обработки операций аутентификации и авторизации.

    Attributes:
        _pwd_context: Контекст для хеширования паролей (использует bcrypt)
    """
    _pwd_context = PasswordHasher()

    @classmethod
    async def get_password_hash(cls, password: SecretStr) -> str:
        """Генерирует хеш пароля.

        Args:
            password: Пароль в чистом виде (обернутый в SecretStr для безопасности)

        Returns:
            str: Хешированная строка пароля
        """
        return cls._pwd_context.hash(password.get_secret_value())

    @classmethod
    async def verify_password(
            cls,
            plain_password: str,
            hashed_password: str
    ) -> bool:
        """Проверяет соответствие пароля и его хеша.

        Args:
            plain_password: Пароль в чистом виде
            hashed_password: Хешированный пароль для проверки

        Returns:
            bool: True если пароль верный, иначе False
        """
        try:
            return cls._pwd_context.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
        except VerificationError as e:
            logger.error(f"Ошибка верификации пароля: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при проверке пароля: {e}")
            return False

    @staticmethod
    async def encode_jwt(
            payload: dict,
            secret_key: str = config.auth_config.SECRET_KEY,
            algorithm: str = config.auth_config.ALGORITHM
    ) -> str:
        """Кодирует данные в JWT токен.

        Args:
            payload: Данные для кодирования
            secret_key: Ключ для подписи (по умолчанию из config)
            algorithm: Алгоритм шифрования (по умолчанию из config)

        Returns:
            str: Закодированный JWT токен
        """
        encoded = jwt.encode(
            payload,
            secret_key,
            algorithm=algorithm,
        )
        return encoded

    @staticmethod
    async def decode_jwt(
            token: str | bytes,
            secret_key: str = config.auth_config.SECRET_KEY,
            algorithm: str = config.auth_config.ALGORITHM
    ) -> dict:
        """Декодирует JWT токен.

        Args:
            token: Токен для декодирования
            secret_key: Ключ для проверки подписи (по умолчанию из config)
            algorithm: Алгоритм шифрования (по умолчанию из config)

        Returns:
            dict: Раскодированные данные из токена

        Raises:
            JWTError: Если токен невалидный
        """
        decoded = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
        )
        return decoded

    @staticmethod
    async def create_token(
            data: dict,
            timedelta_minutes: int,
    ) -> str:
        """Создает JWT токен с указанными параметрами.

        Args:
            data: Основные данные токена (будет добавлены exp и session_id)
            timedelta_minutes: Время жизни токена в минутах (по умолчанию из config)

        Returns:
            str: Получившийся токен
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=timedelta_minutes)
        encode = data.copy()
        encode.update({"exp": expire})
        token = jwt.encode(
            encode,
            key=config.auth_config.SECRET_KEY,
            algorithm=config.auth_config.ALGORITHM
        )
        return token
