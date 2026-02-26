from typing import Annotated, Literal, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, ConfigDict, Field
from pandas import DataFrame


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]
    message_type: str
    messages_length: int = 0
    current_user_input: str
    sql_query: Optional[str] = None
    error_str: Optional[str] = None
    error_attempt: int = 0
    df_len: int = 0
    need_to_optimize: bool = False
    df: Optional[str] = None


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
    