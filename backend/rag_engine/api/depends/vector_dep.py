from fastapi import Query, HTTPException, Request
from typing import Optional

from ....database.session import DatabaseSessionManager
from ...qdrant.manager import VectorStoreManager
from ..schemes.vector_schemes import FieldsDescScheme


def get_fields_description(
        flag: bool = Query(...),
        fields_description: Optional[FieldsDescScheme] = None
) -> Optional[FieldsDescScheme]:
    """Функция, которая проверяет flag и возвращает fields_description при необходимости"""
    if flag and fields_description is None:
        raise HTTPException(
            status_code=400,
            detail="fields_description is required when flag is True"
        )
    return fields_description.fields_description if flag else None


def get_vector_manager(request: Request) -> VectorStoreManager:
    '''Возвращает vector_manager'''
    return request.app.state.vector_manager


async def get_db_manager(request: Request) -> DatabaseSessionManager:
    return request.app.state.db_manager
