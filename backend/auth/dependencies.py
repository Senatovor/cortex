from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from typing import Annotated
from loguru import logger
from jose import JWTError
from sqlalchemy import select

from .models import User
from ..database.session import DbSessionDepends
from ..database.executer import sql_manager
from .handler import AuthHandler
from .scopes_dict import scopes

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth_api/token",
    scopes=scopes,
)

NotAuthException = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Вы не авторизированны",
    headers={"WWW-Authenticate": "Bearer"}
)


async def get_current_user(
        security_scopes: SecurityScopes,
        token: Annotated[str, Depends(oauth2_scheme)],
        db_session: DbSessionDepends()
) -> User:
    """Получает текущего пользователя по JWT токену.

    Args:
        security_scopes(SecurityScopes): Права
        token(str): JWT токен
        db_session(AsyncSession): Сессия базы данных

    Returns:
        Объект пользователя

    Raises:
        NotAuthException(401): Если токен невалидный или пользователь не найден
    """
    try:
        payload = await AuthHandler.decode_jwt(token)
        email = payload.get('sub')
        if email is None:
            raise NotAuthException

        scope: str = payload.get("scope", "")
        token_scopes = scope.split(" ")

        user = await sql_manager(
            select(User).where(User.email == email)
        ).scalar_one_or_none(db_session)

        if user is None:
            logger.error('Не найден пользователь')
            raise NotAuthException

        for scope in security_scopes.scopes:
            if scope not in token_scopes:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not enough permissions",
                    headers={"WWW-Authenticate": f'Bearer scope="{security_scopes.scope_str}"'},
                )
    except JWTError as e:
        logger.error(f'Во время декодирования произошла ошибка: {e}')
        raise NotAuthException

    return user
