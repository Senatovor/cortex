from fastapi.security import OAuth2PasswordRequestForm
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from .models import User
from .handler import AuthHandler
from .schemes import TokenScheme, RegistrateUserScheme
from ..config import config
from ..database.executer import sql_manager


class AuthService:
    @staticmethod
    async def get_token(form_data: OAuth2PasswordRequestForm, db_session: AsyncSession):
        """Аутентифицирует пользователя и генерирует JWT токен доступа.

        Args:
            form_data (OAuth2PasswordRequestForm): Данные формы с логином и паролем
            db_session (AsyncSession): Сессия базы данных

        Returns:
            TokenScheme: Объект с JWT токеном доступа

        Raises:
            HTTPException(401): Если пользователь не найден или пароль неверный
            HTTPException(500): При внутренней ошибке сервера
        """
        try:
            user = await sql_manager(
                select(User).where(User.email == form_data.username)
            ).scalar_one_or_none(db_session)

            if not user:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Пользователь не найден')
            if not await AuthHandler.verify_password(form_data.password, user.password):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Неверный пароль')

            access_token = await AuthHandler.create_token(
                data={"sub": user.email},
                timedelta_minutes=config.auth_config.ACCESS_TOKEN_EXPIRE
            )

            return TokenScheme(
                access_token=access_token,
                token_type='Bearer'
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Ошибка сервера')

    @staticmethod
    async def register(register_user: RegistrateUserScheme, db_session: AsyncSession):
        """Создает нового пользователя в базе данных.

        Args:
            register_user (RegistrateUserScheme): Данные для регистрации
            db_session (AsyncSession): Сессия базы данных

        Returns:
            JSONResponse: Ответ об успешной регистрации

        Raises:
            HTTPException(409): При нарушении уникальности (дубликат пользователя)
            HTTPException(500): При других ошибках базы данных или сервера
        """
        try:
            register_user.password = await AuthHandler.get_password_hash(register_user.password)

            user = await sql_manager(
                insert(User).values(**register_user.model_dump()).returning(User)
            ).scalar_one_or_none(db_session)

            logger.info(f'Пользователь {user.username} зарегистрирован')
            return JSONResponse(
                content={"message": 'Вы зарегистрированы'},
                status_code=status.HTTP_200_OK
            )

        except IntegrityError as e:
            if "unique constraint" in str(e.orig).lower():
                logger.error('Такой пользователь уже есть')
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Конфликт: данные уже существуют")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка сервера")
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Ошибка сервера')
