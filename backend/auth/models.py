from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, ARRAY, String

from ..database.model import Base


class User(Base):
    """ORM-модель пользователя системы.

    Attributes:
        username(str): Логин пользователя. Обязательное поле.
        email(str): Электронная почта пользователя. Должна быть уникальной.
        password(str): Хэшированный пароль пользователя. Хранится в зашифрованном виде.
        is_superuser(bool): Роль пользователя в системе, является ли он админом.
    """
    username: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    is_superuser: Mapped[bool] = mapped_column(default=False, server_default=text('false'), nullable=False)
