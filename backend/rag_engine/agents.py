from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from backend.config import config
from backend.rag_engine.prompts import (
    sql_prompt, sql_agent_prompt,
    deep_talking_agent_prompt, analytic_prompt,
    optimized_sql_prompt  # Новый промпт
)
from backend.rag_engine.rag_scheme import SQLScheme, AnalyticsScheme, OptimizedSQLScheme, QueryIntentScheme


def create_generate_sql_agent():
    model = ChatOllama(
        model=config.rag_config.MODEL_NAME,
        base_url=config.rag_config.MODEL_HOST,
        temperature=config.rag_config.TEMPERATURE,
    )
    agent_generate_sql = create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        system_prompt=sql_agent_prompt,
        response_format=ToolStrategy(SQLScheme),
        middleware=[sql_prompt]
    )
    return agent_generate_sql


def create_optimized_sql_agent():
    """Агент для создания оптимизированных SQL запросов при больших объемах"""
    model = ChatOllama(
        model=config.rag_config.MODEL_NAME,
        base_url=config.rag_config.MODEL_HOST,
        temperature=config.rag_config.TEMPERATURE,
    )
    agent_optimized_sql = create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        system_prompt="""Ты - эксперт по оптимизации SQL запросов.
        На основе исходного запроса и намерений пользователя создай оптимизированный SQL запрос.

        Правила оптимизации:
        1. Для больших объемов используй агрегатные функции (COUNT, AVG, SUM, MIN, MAX)
        2. Группируй данные по логическим категориям (по годам, школам, районам)
        3. Используй LIMIT для выборки топ-N результатов
        4. Для трендов используй группировку по времени
        5. Сохраняй структуру, понятную для аналитики

        Верни JSON с полями sql_query, aggregation_type, original_intent.
        """,
        response_format=ToolStrategy(OptimizedSQLScheme),
        middleware=[optimized_sql_prompt]
    )
    return agent_optimized_sql


def create_deep_talking_agent():
    model = ChatOllama(
        model=config.rag_config.MODEL_NAME,
        base_url=config.rag_config.MODEL_HOST,
        temperature=config.rag_config.TEMPERATURE,
        num_predict=2048,
    )
    agent_deep_talking = create_agent(
        model=model,
        tools=[],
        checkpointer=InMemorySaver(),
        system_prompt=deep_talking_agent_prompt,
    )
    return agent_deep_talking


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
        system_prompt="""
        Ты - классификатор намерений для системы работы с базой данных.
        Определи, что хочет пользователь: просто получить данные или провести анализ.

        Правила классификации:
        - DATA_ONLY: пользователь просит "дай данные", "покажи", "выведи", "список", "таблицу", "поля"
        - ANALYTICS: пользователь просит "проанализируй", "сравни", "тенденция", "динамика", "статистика", "среднее", "максимум", "минимум", "итоги"

        Также оцени объем данных:
        - SMALL: запросы по конкретному ученику, классу, школе (до 100 строк)
        - MEDIUM: запросы по району, нескольким школам (100-1000 строк)
        - LARGE: запросы по всему региону, всем школам (более 1000 строк)

        Верни ответ в формате JSON.
        """,
        response_format=ToolStrategy(QueryIntentScheme)
    )
    return agent_intent_classifier


agent_generate_sql = create_generate_sql_agent()
agent_optimized_sql = create_optimized_sql_agent()
agent_deep_talking = create_deep_talking_agent()
agent_intent_classifier = create_intent_classifier_agent()