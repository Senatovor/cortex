from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from backend.config import config
from backend.rag_engine_v3.rag_schemes import AnalyticScheme, QueryIntentScheme, SQLScheme
from backend.rag_engine_v3.prompts import intent_classifier_prompt, sql_generate_prompt, analytic_prompt


def create_intent_classifier_agent():
    model = ChatOllama(
        model=config.rag_config.MODEL_NAME,
        base_url=config.rag_config.MODEL_HOST,
        temperature=0.1,
    )
    agent_intent_classifier = create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        system_prompt=intent_classifier_prompt,
        response_format=ToolStrategy(QueryIntentScheme)
    )
    return agent_intent_classifier
 
 
def create_sql_generate_agent():
    model = ChatOllama(
        model=config.rag_config.MODEL_NAME,
        base_url=config.rag_config.MODEL_HOST,
        temperature=0.1,
    )
    agent_sql = create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        system_prompt=sql_generate_prompt,
        response_format=ToolStrategy(SQLScheme)
    )
    return agent_sql
 
 
def create_analytic_agent():
    model = ChatOllama(
        model=config.rag_config.MODEL_NAME,
        base_url=config.rag_config.MODEL_HOST,
        temperature=0.1,
    )
    analytic_agent = create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        system_prompt=analytic_prompt,
        response_format=ToolStrategy(AnalyticScheme)
    )
    return analytic_agent
 
 
agent_intent_classifier = create_intent_classifier_agent()
agent_sql_generate = create_sql_generate_agent()
agent_analytic = create_analytic_agent()
 