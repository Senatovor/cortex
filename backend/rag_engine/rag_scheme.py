from typing import Annotated, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages]
    message_type: str
    current_user_input: str
    sql_query: str


class MessageClassificationScheme(BaseModel):
    message_type: Literal["analytics", "question"] = Field(
        description="Тип сообщения: аналитика (analytics) или вопрос (question)"
    )
    confidence: float = Field(
        description="Уверенность в классификации от 0.0 до 1.0",
        ge=0.0, le=1.0
    )


class SQLScheme(BaseModel):
    sql_query: str = Field(description="SQLScheme запрос в PostgreSQL")
