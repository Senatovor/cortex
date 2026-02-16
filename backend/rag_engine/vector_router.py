from fastapi import APIRouter, Query, Depends, HTTPException, Request
from typing import Optional

from ..database.session import DatabaseSessionManager
from ..rag_engine.qdrant import VectorStoreManager
from ..rag_engine.script import ScriptVector
from ..rag_engine.vector_schemes import VectorDbScheme, FieldsDescScheme

vector_router = APIRouter(prefix="/vector", tags=["router"])


# Функция, которая проверяет flag и возвращает fields_description при необходимости
def get_fields_description(
        flag: bool = Query(...),
        fields_description: Optional[FieldsDescScheme] = None
) -> Optional[FieldsDescScheme]:
    if flag and fields_description is None:
        raise HTTPException(
            status_code=400,
            detail="fields_description is required when flag is True"
        )
    return fields_description if flag else None

def get_vector_manager(request: Request) -> VectorStoreManager:
    '''
    Возвращает vector_manager
    '''
    return request.app.state.vector_manager

async def get_db_manager(request: Request) -> DatabaseSessionManager:
    return request.app.state.db_manager


@vector_router.post("/", summary='Создание и добавление векторных представлений')
async def add_vdb(
        vector_database: VectorDbScheme,
        flag: bool = Query(..., description="Флаг для включения fields_description"),
        fields_description: Optional[FieldsDescScheme] = Depends(get_fields_description),
        vector_manager: VectorStoreManager = Depends(get_vector_manager),
        db_manager: DatabaseSessionManager = Depends(get_db_manager)
) -> dict:
    """
    Создает и добавляет векторные представления в векторную базу данных.

    Эндпоинт принимает данные для векторизации и опциональное описание полей,
    после чего запускает процесс создания векторных представлений и их сохранения
    в векторной БД.

    Args:
        vector_database (VectorDbScheme): Схема с данными для векторизации, содержащая
            информацию о том, какие данные нужно преобразовать в векторные представления.

        flag (bool): Обязательный query-параметр, определяющий необходимость использования
            описания полей при векторизации:
            - True: использовать описание полей из fields_description
            - False: не использовать описание полей

        fields_description (Optional[FieldsDescScheme], optional): Описание полей для
            более точной векторизации. Загружается через Depends. По умолчанию None.

        vector_manager (VectorStoreManager): Менеджер для работы с векторным хранилищем,
            получаемый через Dependency Injection. Отвечает за операции с векторной БД.

        db_manager (DatabaseSessionManager): Менеджер сессий базы данных для работы
            с реляционной БД. Получается через DbSessionDepends().

    Returns:
        dict: Словарь с результатом операции:
            - success (bool): True если операция успешна
            - message (str): Сообщение о результате операции

    Raises:
        HTTPException: Исключение с кодом 404 возникает в случае ошибки при добавлении
            данных в векторную БД. Текст ошибки передается в detail.
    """
    script = ScriptVector(
        db_session_manager=db_manager,
        vector_store_manager=vector_manager
    )
    try:
        if flag:
            await script.add_data_to_vdb(vector_database.vector_database, vector_manager, fields_description)
            return {'success': True, 'message': 'Представления загружены в бд'}
        else:
            await script.add_data_to_vdb(vector_database.vector_database, vector_manager)
            return {'success': True, 'message': 'Представления загружены в бд'}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@vector_router.post('/search')
async def search_vdb(
        vector_database: VectorDbScheme,
        query: str = Query(...),
        vector_manager: VectorStoreManager = Depends(get_vector_manager),
):
    vector_store = vector_manager.get_vector_store(vector_database.vector_database)
    results = vector_store.similarity_search(query)
    return {'message': 'ok', 'results': results}