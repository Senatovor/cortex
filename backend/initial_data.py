import asyncio
import subprocess
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from backend.auth.handler import AuthHandler
from backend.auth.models import User
from backend.config import config
from backend.database.executer import sql_manager
from backend.database.session import session_manager
from backend.auth.schemes import RegistrateUserScheme


class AdminCreateScheme(RegistrateUserScheme):
    is_superuser: bool = True


async def check_and_create_migrations():
    try:
        logger.info("Применяю миграции...")
        apply_result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )

        if apply_result.returncode == 0:
            logger.success("Миграции успешно применены")
        else:
            logger.error(f"Ошибка при применении миграций: {apply_result.stderr}")

    except FileNotFoundError:
        logger.error("Alembic не найден. Убедитесь, что он установлен и доступен в PATH")
    except KeyboardInterrupt:
        logger.info("Создание миграции отменено пользователем")
    except Exception as e:
        logger.error(f"Ошибка при работе с миграциями: {str(e)}")


@session_manager.connection(commit=True)
async def create_admin(db_session: AsyncSession):
    logger.info("Проверяю наличие администратора...")
    admin = await sql_manager(
        select(User).where(
            User.username == config.ADMIN_NAME,
            User.email == config.ADMIN_EMAIL,
            User.is_superuser == True
        )
    ).scalar_one_or_none(db_session)

    if not admin:
        register_user = AdminCreateScheme(
            username=config.ADMIN_NAME,
            email=config.ADMIN_EMAIL,
            password=config.ADMIN_PASSWORD
        )
        register_user.password = await AuthHandler.get_password_hash(register_user.password)
        await sql_manager(
            insert(User).values(**register_user.model_dump())
        ).execute(db_session)
        logger.success("Администратор создан успешно")
    else:
        logger.info("Администратор уже существует")


async def main():
    logger.info("Начинаю процесс инициализации данных...")

    await session_manager.init()

    # 1. Проверяем и создаем миграции
    await check_and_create_migrations()

    # 2. Создаем администратора
    await create_admin()

    logger.success("Инициализация данных завершена успешно!")


if __name__ == "__main__":
    asyncio.run(main())
