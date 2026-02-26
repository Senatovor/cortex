from datetime import datetime
import os
import uuid
import pandas as pd
from langchain_core.runnables import RunnableConfig
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy import create_engine
import polars as pl
from pathlib import Path

from .agents import agent_intent_classifier, agent_analytic, agent_sql_generate
from .rag_schemes import AgentState
from .handler import get_schema_db_info


async def user_input_node(state: AgentState) -> dict:
    dialog_messages = [m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))]
    messages_length = len(dialog_messages)
    print(f'Сообщений: {messages_length}')
    return {
        'messages_length': messages_length
    }


async def classify_intent_node(state: AgentState) -> dict:
    current_user_input = state.current_user_input
    try:
        result = await agent_intent_classifier.ainvoke(
            input={'messages': [HumanMessage(content=current_user_input)]},
            config={'configurable': {'thread_id': 'intent_session'}},
        )
        intent = result['structured_response']
        print(f'Определено намерение: {intent.intent_type}')
        return {
            'message_type': intent.intent_type
        }
    except Exception as e:
        logger.error(f'Ошибка классификации: {e}')
        return {
            'message_type': 'other'
        }
    

async def data_node(state: AgentState, config: RunnableConfig) -> dict:
    current_user_input = state.current_user_input
    error_str = state.error_str
    error_attempt = state.error_attempt
    try:
        vector_manager = config['configurable'].get('vector_manager') # type: ignore
        schema_info = await get_schema_db_info(current_user_input, vector_manager) # type: ignore
        print('Создаю sql запрос...')
        if not error_str:
            messages = [
                SystemMessage(content=f'Сейчас будет запрос на получение данных, вот структура базы: {schema_info}'),
                HumanMessage(content=current_user_input)
            ]
        else:
            messages = [
                SystemMessage(content=f'Ошибка предыдущего запроса({current_user_input}). Исправь ошибку с учетом структуры БД: {error_str}')
            ]
        result = await agent_sql_generate.ainvoke(
            input={'messages': messages}, # type: ignore
            config={'configurable': {'thread_id': 'sql_generate_session'}}
        )
        sql_query = result['structured_response'].sql_query
        print(f'Созданный запрос SQL: {sql_query}')
        
        db_session = config['configurable'].get('db_session') # type: ignore
        df = pl.read_database(query=sql_query, connection=db_session) # type: ignore
        filepath = Path(__file__).parent.parent.parent / 'files' / 'xlsx' / f'query_result_{uuid.uuid4()}.xlsx'
        df.write_excel(
            filepath.as_posix(),
            worksheet='List1',
            autofit=True,
        )
        
        return {
            'messages': [AIMessage(content='Ваш запрос на получение данных был выполенен и записан в excel файл')],
            'sql_query': sql_query,
            'error_str': None,
            'error_attempt': 0
        }
        
    except Exception as e:
        logger.error(f'Ошибка генерации SQL: {e}')
        if error_attempt > 3:
            return {
                'messages': [AIMessage(content='Извините, произошла ошибка при формировании запроса.')],
                'error_str': None,
                'error_attempt': 0
            }
        return {
            'error': str(e),
            'error_attempt': state.error_attempt + 1
        }


async def statistics_node(state: AgentState, config: RunnableConfig) -> dict:
    current_user_input = state.current_user_input
    error_str = state.error_str
    error_attempt = state.error_attempt
    
    try:
        vector_manager = config['configurable'].get('vector_manager') # type: ignore
        schema_info = await get_schema_db_info(current_user_input, vector_manager) # type: ignore
        print('Создаю sql запрос...')
        if not error_str:
            messages = [
                SystemMessage(content=f'Сейчас будет запрос на получение статистики, вот структура базы: {schema_info}'),
                HumanMessage(content=current_user_input)
            ]
        else:
            messages = [
                SystemMessage(content=f'Ошибка предыдущего запроса({current_user_input}). Исправь ошибку с учетом структуры БД: {error_str}')
            ]
        
        result = await agent_sql_generate.ainvoke(
            input={'messages': messages}, # type: ignore
            config={'configurable': {'thread_id': 'sql_generate_session'}},
        )
        sql_query = result['structured_response'].sql_query
        print(f'Сгенерированный SQL: {sql_query}')
        
        db_session = config['configurable'].get('db_session') # type: ignore
        df = pl.read_database(query=sql_query, connection=db_session) # type: ignore
        filepath = Path(__file__).parent.parent.parent / 'files' / 'xlsx' / f'query_result_{uuid.uuid4()}.xlsx'
        df.write_excel(
            filepath.as_posix(),
            worksheet='List1',
            autofit=True,
        )
        
        return {
            'messages': [AIMessage(content='Ваш запрос на получение статистики был выполнен и записан в excel файл')],
            'sql_query': sql_query,
            'error': None,
            'error_attempt': 0
        }
        
    except Exception as e:
        logger.error(f'Ошибка генерации SQL: {e}')
        if error_attempt >= 3:
            return {
                'messages': [AIMessage(content='Извините, произошла ошибка при формировании запроса.')],
                'error': None,
                'error_attempt': 0,
            }
        return {
            'error': str(e),
            'error_attempt': state.error_attempt + 1
        }


async def generate_sql_analytic_node(state: AgentState, config: RunnableConfig) -> dict:
    current_user_input = state.current_user_input
    error_str = state.error_str
    error_attempt = state.error_attempt
    need_to_optimize = state.need_to_optimize
    df_len = state.df_len
    
    try:
        vector_manager = config['configurable'].get('vector_manager') # type: ignore
        schema_info = await get_schema_db_info(current_user_input, vector_manager) # type: ignore
        print('Создаю sql запрос...')
        
        if not error_str:
            messages = [
                SystemMessage(content=f'Сейчас будет запрос на аналитику, вот структура базы: {schema_info}'),
                HumanMessage(content=current_user_input)
            ]
        elif need_to_optimize:
            messages = [
                SystemMessage(content=f'Предыдущий SQL запрос({state.sql_query}) вернул слишком много данных: {df_len}. Улучшь или сделай более точный запрос')
            ]
        else:
            messages = [
                SystemMessage(content=f'Ошибка предыдущего запроса({current_user_input}). Исправь ошибку с учетом структуры БД: {error_str}')
            ]
        result = await agent_analytic.ainvoke(
            input={'messages': messages}, # type: ignore
            config={'configurable': {'thread_id': 'sql_generate_session'}},
        )
        sql_query = result['structured_response'].sql_query
        print(f'Сгенерированный SQL: {sql_query}')
        
        db_session = config['configurable'].get('db_session') # type: ignore
        df = pl.read_database(query=sql_query, connection=db_session) # type: ignore
        print(f'Запрос выполнен успешно, получено {len(df)} записей')
        df_json = df.write_json()
        print(df_json)
        
        return {
            'df': df_json,
            'sql_query': sql_query,
            'error': None,
            'error_attempt': 0
        }
        
    except Exception as e:
        logger.error(f'Ошибка генерации SQL: {e}')
        if error_attempt >= 3:
            return {
                'messages': [AIMessage(content='Извините, произошла ошибка при формировании запроса.')],
                'error': None,
                'error_attempt': 0,
            }
        return {
            'error': str(e),
            'error_attempt': state.error_attempt + 1
        }


async def analytic_node(state: AgentState):
    sql_query = state.sql_query
    df = state.df
    
    try:
        result = await agent_analytic.ainvoke(
            input={'messages': [SystemMessage(content=f'Напиши аналитику по запросу пользователя на sql запросу {sql_query} на эти данные {df}')]},
            config={'configurable': {'thread_id': 'analys_session'}},
        )
        answer = result['structured_response'].answer
        return {
            'messages': [AIMessage(content=answer)]
        }
    except Exception as e:
        logger.error(str(e))
        error_message = AIMessage(
                content='Извините, произошла ошибка при формировании запроса. '
                        'Попробуйте переформулировать запрос или уточнить названия полей.'
            )
        return {'messages': [error_message],}
    