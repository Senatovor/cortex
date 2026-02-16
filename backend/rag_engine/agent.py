from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent

from backend.config import config

model = ChatOllama(
    model=config.rag_config.MODEL_NAME,
    base_url=config.rag_config.MODEL_HOST,
    temperature=config.rag_config.TEMPERATURE,
)

system_prompt = 'Ты крутой мужик'

checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=None,
    checkpointer=checkpointer,
    system_prompt=SystemMessage(content=system_prompt)
)
