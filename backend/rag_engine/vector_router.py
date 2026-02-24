import asyncio
import json
import uuid

from fastapi import APIRouter, Query, Depends, HTTPException, Request
from typing import Optional
from langchain_qdrant import QdrantVectorStore
from loguru import logger

from ..database.session import DatabaseSessionManager
from ..rag_engine.qdrant import VectorStoreManager
from ..rag_engine.script import ScriptVector
from ..rag_engine.vector_schemes import VectorDbScheme, FieldsDescScheme, PointUpdateScheme, PointResponseSchema

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
    return fields_description.fields_description if flag else None



def get_vector_manager(request: Request) -> VectorStoreManager:
    '''
    Возвращает vector_manager
    '''
    return request.app.state.vector_manager

async def get_db_manager(request: Request) -> DatabaseSessionManager:
    return request.app.state.db_manager


@vector_router.get('/points', summary='Получение точек из всех коллекций')
async def get_points(
        vector_manager: VectorStoreManager = Depends(get_vector_manager),
):
    points = await ScriptVector.get_all_points(vector_manager=vector_manager)
    return points

@vector_router.get("/schema", summary='Получение схемы базы данных')
async def get_db_schema(
        db_manager: DatabaseSessionManager = Depends(get_db_manager)
) -> dict:
    """
    Возвращает схему базы данных: список таблиц и их колонок.

    Returns:
        dict: Словарь, где ключ - имя таблицы, значение - список названий колонок

    Example:
        {
            "users": ["id", "email", "created_at"],
            "orders": ["id", "user_id", "total"]
        }
    """
    logger.info('Запрос схемы базы данных')
    try:
        script = ScriptVector(db_session_manager=db_manager)
        schema = await script.get_db_schema()
        logger.info(f'Схема получена: {len(schema)} таблиц')
        return schema
    except Exception as e:
        logger.error(f'Ошибка получения схемы БД: {e}')
        raise HTTPException(status_code=500, detail=f'Ошибка получения схемы БД: {str(e)}')

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
    logger.info('Инициализация скрипта Vector')
    script = ScriptVector(
        db_session_manager=db_manager,
        vector_store_manager=vector_manager
    )
    try:
        if flag:
            logger.info('Добавление векторного представления в бд')
            await script.add_data_to_vdb(
                collection_name=vector_database.vector_database,
                vector_manager=vector_manager,
                fields_description=fields_description)
            return {'success': True, 'message': 'Представления загружены в бд'}
        else:
            logger.info('Добавление векторного представления в бд')
            await script.add_data_to_vdb(
                collection_name=vector_database.vector_database,
                vector_manager=vector_manager,
                fields_description=fields_description)
            return {'success': True, 'message': 'Представления загружены в бд'}
    except Exception as e:
        logger.error(f'Ошибка загрузки представлений {e}')
        raise HTTPException(status_code=404, detail=f'Ошибка загрузки представлений {e}')

@vector_router.put('/update_point', summary='Обновление точки')
async def update_vdb(
    point: PointUpdateScheme,
    collection_name: VectorDbScheme,
    vector_manager: VectorStoreManager = Depends(get_vector_manager),
) -> dict:
    """
       Обновляет или создает точку в векторной базе данных.

       Parameters
       ----------
       point : PointUpdateScheme
           Схема данных точки, содержащая:
           - id: уникальный идентификатор
           - table_name: название таблицы
           - value: значение для векторизации
       collection_name : VectorDbScheme
           Схема с названием векторной базы данных, куда будет добавлена точка
       vector_manager : VectorStoreManager
           Менеджер векторных хранилищ для получения соответствующего VectorStore
           (внедряется через зависимость)

       Returns
       -------
       dict
           Словарь с результатом операции:
           - success: булево значение успешности операции
           - message: текстовое сообщение о результате

       Notes
       -----
       Функция асинхронно выполняет добавление текста в векторное хранилище.
       Текст для векторизации формируется из названия таблицы и значения.
       Метаданные сохраняются вместе с вектором для последующего поиска.
    """
    try:
        logger.info('Получение vector_store')
        vector_store = vector_manager.get_vector_store(collection_name.vector_database)
        text = f'Название таблицы: {point.table_name} Значения и описания: {point.value}'
        logger.info('Обновление точки')
        await vector_store.aadd_texts(
            ids=[point.id],
            texts=[text],
            metadatas=[{
                'table_name': point.table_name,
                'value': point.value
            }]
        )
        return {'success': True, 'message': f'Точка {point.table_name} обновлена'}
    except Exception as e:
        logger.error(f'Ошибка обновления {e}')
        raise HTTPException(status_code=404, detail=f'Ошибка обновления {e}')

@vector_router.post('/search')
async def search_vdb(
        vector_database: VectorDbScheme,
        query: str = Query(...),
        vector_manager: VectorStoreManager = Depends(get_vector_manager),
) -> dict:
    """
    Выполняет поиск по векторной базе данных на основе текстового запроса.

    Parameters
    ----------
    vector_database : VectorDbScheme
        Схема, определяющая целевую векторную базу данных для поиска
    query : str
        Текстовый запрос для поиска семантически близких результатов
        (обязательный параметр Query)
    vector_manager : VectorStoreManager
        Менеджер векторных хранилищ для получения соответствующего VectorStore
        (внедряется через зависимость)

    Returns
    -------
    dict
        Словарь с результатами поиска:
        - message: статус операции ('ok')
        - results: список найденных документов/точек, отсортированных по релевантности

    Notes
    -----
    Функция использует семантический поиск (similarity search) для нахождения
    наиболее релевантных результатов по заданному текстовому запросу.
    """
    vector_store = vector_manager.get_vector_store(vector_database.vector_database)
    results = vector_store.similarity_search(query)
    return {'message': 'ok', 'results': results}