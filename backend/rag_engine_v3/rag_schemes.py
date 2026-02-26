from typing import Annotated, Literal, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, ConfigDict, Field
from pandas import DataFrame


class QueryIntentScheme(BaseModel):
    """Определяет намерение пользователя в запросе"""
    intent_type: Literal["data", "statistics", "analytics", "other"] = Field(
        description="Тип намерения: данные, статистика, аналитика или иной вопрос",
        default="other"
    )
    
    
class SQLScheme(BaseModel):
    sql_query: str = Field(description="SQL запрос в PostgreSQL")
    

class AnalyticScheme(BaseModel):
    answer: str = Field(description='Твой ответ на запрос пользователя в стиле Markdown')
    