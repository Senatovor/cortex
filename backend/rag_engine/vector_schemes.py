from dataclasses import field

from pydantic import BaseModel, Field


class VectorDbScheme(BaseModel):
    vector_database: str = Field(...,
                                       example='collection_name',
                                       description='Список заполняемых коллекций'
                                       )


class FieldsDescScheme(BaseModel):
    fields_description: dict[str, dict] = Field(example={'table1_name': {'field1': 'desc1', 'field2': 'desc2'},
                                                         'table2_name': {'field1': 'desc1', 'field2': 'desc2'}
                                                         })
