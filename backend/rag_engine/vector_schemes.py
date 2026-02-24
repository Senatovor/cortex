import uuid
from dataclasses import field
from typing import Optional

from pydantic import BaseModel, Field


class VectorDbScheme(BaseModel):
    vector_database: str = Field(
        ...,
        example='collection_name',
        description='Список заполняемых коллекций'
    )


class FieldsDescScheme(BaseModel):
    fields_description: dict[str, dict] = Field(example={
        'table1_name': {'field1': 'desc1', 'field2': 'desc2'},
        'table2_name': {'field1': 'desc1', 'field2': 'desc2'}
    })


class PointResponseSchema(BaseModel):
    id: uuid.UUID = Field(...)
    table_name: str = Field(..., )
    value: dict = Field(...)

    @classmethod
    def format_point(cls, point):
        id = point.id
        payload = point.payload

        return cls(
            id=id,
            table_name=payload['metadata']['table_name'],
            value=payload['metadata']['value']
        )


class PointUpdateScheme(BaseModel):
    id: uuid.UUID = Field(..., description='ID точки')
    table_name: str = Field(
        ...,
        description='Название таблицы',
        example='table_name',
    )
    value: dict = Field(
        ...,
        description='Поля и описания',
        example={
            'field1': 'desc1',
            'field2': 'desc2'
        })
