from typing import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class GraphState(BaseModel):
    messages: Annotated[list[BaseMessage], add_messages] = []
    message_type: str | None = None
    messages_length: int = 0
    current_user_input: str
    sql_query: str | None = None
    error_str: str | None = None
    error_attempt: int = 0
    df_len: int = 0
    need_to_optimize: bool = False
    df: str | None = None
