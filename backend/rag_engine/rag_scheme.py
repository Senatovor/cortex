from typing import Annotated, Literal, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]
    message_type: str
    current_user_input: str
    sql_query: str
    data_summary: list
    query_intent: Optional[dict] = None  # Информация о намерении пользователя
    data_volume: Optional[str] = None  # small, medium, large
    processed_data: Optional[Any] = None  # Обработанные/сокращенные данные


class MessageClassificationScheme(BaseModel):
    message_type: Literal["analytics", "question"] = Field(
        description="Тип сообщения: аналитика (analytics) или вопрос (question)"
    )
    confidence: float = Field(
        description="Уверенность в классификации от 0.0 до 1.0",
        ge=0.0, le=1.0
    )


class QueryIntentScheme(BaseModel):
    """Определяет намерение пользователя в запросе"""
    intent_type: Literal["data_only", "analytics", "unknown"] = Field(
        description="Тип намерения: только данные, аналитика или неизвестно"
    )
    requires_analytics: bool = Field(
        description="Требуется ли аналитическая обработка данных"
    )
    data_volume_estimate: Literal["small", "medium", "large", "unknown"] = Field(
        description="Предполагаемый объем данных"
    )
    key_metrics: list[str] = Field(
        default_factory=list,
        description="Ключевые метрики для анализа (если нужны)"
    )
    aggregation_needed: bool = Field(
        description="Нужна ли агрегация данных"
    )


class SQLScheme(BaseModel):
    sql_query: str = Field(description="SQL запрос в PostgreSQL")
    estimated_row_count: Optional[int] = Field(
        default=None,
        description="Примерное количество строк (если можно оценить)"
    )


class OptimizedSQLScheme(BaseModel):
    """Для оптимизированных SQL запросов при больших объемах"""
    sql_query: str = Field(description="Оптимизированный SQL запрос с агрегацией")
    aggregation_type: str = Field(
        description="Тип агрегации (summary, stats, top_n, etc)"
    )
    original_intent: str = Field(description="Исходное намерение запроса")


class AnalyticsScheme(BaseModel):
    analytic: str = Field(description='Аналитика ответа, если анализировать нечего, просто дай комментарий')
    data: str = Field(description='Данные, если их очень много, дай просто краткую сводку')
    