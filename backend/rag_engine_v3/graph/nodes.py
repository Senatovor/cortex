import uuid
from langchain_core.runnables import RunnableConfig
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
import polars as pl
from pathlib import Path
from polars import DataFrame

from backend.rag_engine_v3.agents import agent_intent_classifier, agent_analytic, agent_sql_generate
from backend.rag_engine_v3.graph.state import GraphState


class Nodes:
    @staticmethod
    async def _get_schema_db_info_for_vector(input: str, config: RunnableConfig) -> str | None:
        try:
            vector_manager = config['configurable'].get('vector_manager')
            structure_store = vector_manager.get_vector_store('structure')
            sql_info_scheme = await structure_store.asimilarity_search(input)
            logger.info(f"Найдено {len(sql_info_scheme)} релевантных таблиц")
            if not sql_info_scheme:
                return None
            schema_info = ""
            for doc in sql_info_scheme:
                table_name = doc.metadata.get('table_name', 'unknown')
                schema_info += f"Таблица: {table_name}\n"
                schema_info += f"Описание: {doc.page_content}\n\n"
            return schema_info
        except Exception as e:
            logger.error(f'Ошибка получения данных из векторки: {e}')
            return None

    @staticmethod
    async def _execute_query_to_df(query: str, config: RunnableConfig) -> DataFrame:
        db_session = config['configurable'].get('db_session')
        df = pl.read_database(query=query, connection=db_session)
        return df

    async def _write_excel_and_csv_from_sql_data(self, query: str, config: RunnableConfig):
        df = await self._execute_query_to_df(query, config)
        filepath = Path(__file__).parent.parent.parent / 'files' / 'xlsx' / f'query_result_{uuid.uuid4()}.xlsx'
        df.write_excel(
            filepath.as_posix(),
            worksheet='List1',
            autofit=True,
        )
        df.write_csv(filepath.as_posix())

    async def _write_json_from_sql_data(self, query: str, config: RunnableConfig):
        df = await self._execute_query_to_df(query, config)
        logger.info(f'Запрос выполнен успешно, получено {len(df)} записей')
        df_json = df.write_json()
        return df_json

    async def _generate_sql_and_execute(
            self,
            input_messages: list[BaseMessage],
            error_attempt: int,
            config: RunnableConfig,
            need_write: bool = False,
            need_return_df: bool = False,
            output_messages: list[BaseMessage] | None = None,
    ) -> dict:
        try:
            result = await agent_sql_generate.ainvoke({'messages': input_messages})
            sql_query = result['structured_response'].sql_query
            logger.info(f'Сгенерированный SQL: {sql_query}')
            response = {
                'sql_query': sql_query,
                'error': None,
                'error_attempt': 0
            }
            if output_messages:
                response['messages'] = output_messages
            if need_write:
                await self._write_excel_and_csv_from_sql_data(sql_query, config)
            if need_return_df:
                json_df = await self._write_json_from_sql_data(sql_query, config)
                response['df'] = json_df

            return response

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
                'error_attempt': error_attempt + 1
            }

    @staticmethod
    async def user_input_node(state: GraphState) -> dict:
        dialog_messages = [m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))]
        messages_length = len(dialog_messages)
        logger.info(f'Сообщений: {messages_length}')
        return {
            'messages_length': messages_length
        }

    @staticmethod
    async def classify_intent_node(state: GraphState) -> dict:
        current_user_input = state.current_user_input
        try:
            result = await agent_intent_classifier.ainvoke({'messages': [HumanMessage(content=current_user_input)]})
            intent = result['structured_response']
            logger.info(f'Определено намерение: {intent.intent_type}')
            return {
                'message_type': intent.intent_type
            }
        except Exception as e:
            logger.error(f'Ошибка классификации: {e}')
            return {
                'message_type': 'other'
            }

    async def data_node(self, state: GraphState, config: RunnableConfig) -> dict:
        current_user_input = state.current_user_input
        error_str = state.error_str
        error_attempt = state.error_attempt

        schema_info = await self._get_schema_db_info_for_vector(current_user_input, config)
        logger.info('Создаю sql запрос...')
        if not error_str:
            messages = [
                SystemMessage(content=f'Сейчас будет запрос на получение данных, вот структура базы: {schema_info}'),
                HumanMessage(content=current_user_input)
            ]
        else:
            messages = [
                SystemMessage(
                    content=f'Ошибка предыдущего запроса({current_user_input}).'
                            f'Исправь ошибку с учетом структуры БД: {error_str}')
            ]

        answer = await self._generate_sql_and_execute(
            input_messages=messages,
            output_messages=[AIMessage(content='Ваш запрос на получение данных был выполнен и записан в excel файл')],
            error_attempt=error_attempt,
            config=config,
            need_write=True
        )
        return answer

    async def statistics_node(self, state: GraphState, config: RunnableConfig) -> dict:
        current_user_input = state.current_user_input
        error_str = state.error_str
        error_attempt = state.error_attempt

        schema_info = await self._get_schema_db_info_for_vector(current_user_input, config)
        logger.info('Создаю sql запрос...')
        if not error_str:
            messages = [
                SystemMessage(
                    content=f'Сейчас будет запрос на получение статистики, вот структура базы: {schema_info}'),
                HumanMessage(content=current_user_input)
            ]
        else:
            messages = [
                SystemMessage(
                    content=f'Ошибка предыдущего запроса({current_user_input}).'
                            f'Исправь ошибку с учетом структуры БД: {error_str}')
            ]

        answer = await self._generate_sql_and_execute(
            input_messages=messages,
            output_messages=[
                AIMessage(content='Ваш запрос на получение статистики был выполнен и записан в excel файл')],
            error_attempt=error_attempt,
            need_write=True,
            config=config,
        )
        return answer

    async def generate_sql_analytic_node(self, state: GraphState, config: RunnableConfig) -> dict:
        current_user_input = state.current_user_input
        error_str = state.error_str
        error_attempt = state.error_attempt
        need_to_optimize = state.need_to_optimize
        df_len = state.df_len

        schema_info = await self._get_schema_db_info_for_vector(current_user_input, config)
        logger.info('Создаю sql запрос...')
        if not error_str:
            messages = [
                SystemMessage(content=f'Сейчас будет запрос на аналитику, вот структура базы: {schema_info}'),
                HumanMessage(content=current_user_input)
            ]
        elif need_to_optimize:
            messages = [
                SystemMessage(
                    content=f'Предыдущий SQL запрос({state.sql_query}) вернул слишком много данных: {df_len}.'
                            f'Улучши или сделай более точный запрос')
            ]
        else:
            messages = [
                SystemMessage(
                    content=f'Ошибка предыдущего запроса({current_user_input}).'
                            f'Исправь ошибку с учетом структуры БД: {error_str}')
            ]
        answer = await self._generate_sql_and_execute(
            input_messages=messages,
            error_attempt=error_attempt,
            need_return_df=True,
            config=config
        )
        return answer

    @staticmethod
    async def analytic_node(state: GraphState):
        sql_query = state.sql_query
        df = state.df
        try:
            result = await agent_analytic.ainvoke(
                {'messages': [SystemMessage(content=f'Напиши аналитику по запросу пользователя '
                                                    f'на sql запросу {sql_query} на эти данные {df}')]}
            )
            answer = result['structured_response'].answer
            return {'messages': [AIMessage(content=answer)]}
        except Exception as e:
            logger.error(str(e))
            error_message = AIMessage(
                content='Извините, произошла ошибка при формировании запроса. '
                        'Попробуйте переформулировать запрос или уточнить названия полей.'
            )
            return {'messages': [error_message]}
