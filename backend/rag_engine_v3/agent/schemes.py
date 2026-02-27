from typing import Literal
from pydantic import BaseModel, Field


class QueryIntentScheme(BaseModel):
    intent_type: Literal["data", "statistics", "analytics", "other"] = Field(
        description="Тип намерения: данные, статистика, аналитика или иной вопрос",
        default="other"
    )
    
    
class SQLScheme(BaseModel):
    sql_query: str = Field(description="SQL запрос в PostgreSQL")
    

class AnalyticScheme(BaseModel):
    answer: str = Field(description='Твой ответ на запрос пользователя в стиле Markdown')
    