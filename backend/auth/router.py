from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from typing import Annotated

from .dependencies import get_current_user
from ..database.session import DbSessionDepends
from .service import AuthService
from .schemes import RegistrateUserScheme, SystemUserScheme
from .schemes import TokenScheme

auth_api_router = APIRouter(
    prefix='/auth_api',
    tags=['auth'],
)


@auth_api_router.post('/token', name='token', response_model=TokenScheme)
async def token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db_session: DbSessionDepends(),
) -> TokenScheme:
    """Выпускает JWT токен доступа при успешной аутентификации.

    Args:
        form_data (OAuth2PasswordRequestForm): Данные формы с логином и паролем
        db_session (AsyncSession): Сессия базы данных

    Returns:
        TokenScheme: Объект с JWT токеном доступа и типом токена

    Raises:
        HTTPException(401): Если пользователь не найден или пароль неверный
        HTTPException(500): При внутренней ошибке сервера
    """
    return await AuthService.get_token(form_data, db_session)


@auth_api_router.post('/register', name='register', response_class=JSONResponse)
async def register(
        register_user: RegistrateUserScheme,
        session: DbSessionDepends(commit=True)
):
    """Регистрирует нового пользователя в системе.

    Args:
        register_user (RegistrateUserScheme): Данные для регистрации пользователя
        session (AsyncSession): Сессия базы данных с авто-коммитом

    Returns:
        JSONResponse: Сообщение об успешной регистрации

    Raises:
        HTTPException(409): Если пользователь с таким именем уже существует
        HTTPException(500): При внутренней ошибке сервера
    """
    return await AuthService.register(register_user, session)


@auth_api_router.get('/info', name='users-info', response_model=SystemUserScheme)
async def user_info(user: Annotated[SystemUserScheme, Depends(get_current_user)]):
    """Получить основную информацию об авторизированном юзере"""
    return user
