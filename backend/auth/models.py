from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, ARRAY, String

from .scopes_dict import default_scopes_users
from ..database.model import Base


class User(Base):
    """ORM-модель пользователя системы.

    Attributes:
        username(str): Логин пользователя. Обязательное поле.
        email(str): Электронная почта пользователя. Должна быть уникальной.
        password(str): Хэшированный пароль пользователя. Хранится в зашифрованном виде.
        scopes: Права допустимые пользователю в системе
    """
    username: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=default_scopes_users,
        server_default=text(f"ARRAY{default_scopes_users}"),
    )
