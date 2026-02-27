import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from loguru import logger
from pydantic import BaseModel

from backend.database.session import session_manager, DatabaseSessionManager
from backend.config import config
from backend.auth.router import auth_api_router
from backend.rag_engine.api.routers.vector_router import vector_router
from backend.rag_engine.qdrant.manager import VectorStoreManager, vector_manager


class AppState(BaseModel):
    db_manager: DatabaseSessionManager
    vector_manager: VectorStoreManager

    model_config = {'arbitrary_types_allowed': True}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Контекстный менеджер для управления жизненным циклом приложения.

    Args:
        app: Экземпляр FastAPI приложения
    """
    app.state: AppState

    # Инициализация сессий sql базы
    await session_manager.init()
    # Инициализация менеджера векторной базы
    await vector_manager.init()

    app.state.db_manager = session_manager
    app.state.vector_manager = vector_manager
    
    yield

    # Очистка
    await app.state.db_manager.close()
    await app.state.vector_manager.close()


def create_app() -> FastAPI:
    """Фабрика для создания и настройки экземпляра FastAPI.

    Returns:
        FastAPI: Настроенный экземпляр FastAPI приложения
    """
    app = FastAPI(
        title=config.TITLE,
        version=config.VERSION,
        description=config.description_project,
        contact=config.contact_project,
        docs_url=config.DOCS_URL,
        redoc_url=config.REDOC_URL,
        lifespan=lifespan
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_api_router)  # Установка роутера авторизации
    app.include_router(vector_router) # Установка роутера векторной бд

    return app


if __name__ == '__main__':
    try:
        logger.info('Запуск приложения...')
        logger.add(
            Path(__file__).parent.parent / "app.log",
            rotation=config.logger_config.ROTATION,
            level=config.logger_config.LEVEL,
            backtrace=config.logger_config.BACKTRACE,
            diagnose=config.logger_config.DIAGNOSE,
            enqueue=config.logger_config.ENQUEUE,
            catch=config.logger_config.CATCH,
            compression=config.logger_config.COMPRESSION,
        )
        app = create_app()
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=5000,
            log_config=None,
            log_level=None,
        )
        logger.info('Приложение запущено')

    except Exception as e:
        logger.error(f'Во время создания приложения произошла ошибка: {e}')
