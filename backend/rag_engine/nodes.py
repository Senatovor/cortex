import uuid
import pandas as pd
from loguru import logger
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ..config import config
from .agents import agent_generate_sql, agent_deep_talking, agent_optimized_sql, agent_intent_classifier
from .qdrant import vector_manager
from .rag_scheme import AgentState


def user_input(state: AgentState):
    """Просто пропускает ввод, который пришел извне"""
    return {
        "messages": [HumanMessage(content=state.current_user_input)]
    }


def check_to_end(state: AgentState):
    """Проверка лимита истории"""
    dialog_messages = [m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))]

    if len(dialog_messages) >= 45:
        print('Контекст переполнен')
        return 'end'
    print(f'Сообщений: {len(dialog_messages)}')
    return 'continue'


def classify_intent_node(state: AgentState):
    """Узел классификации намерения пользователя"""
    user_input = state.current_user_input

    try:
        # Асинхронно классифицируем намерение
        result = agent_intent_classifier.invoke(
            input={"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"thread_id": 'intent_session'}},
        )
        intent = result['structured_response']

        print(f"🔍 Определено намерение: {intent.intent_type}")
        print(f"📊 Требуется аналитика: {intent.requires_analytics}")
        print(f"📈 Оценка объема: {intent.data_volume_estimate}")

        return {
            "query_intent": intent.dict(),
            "message_type": intent.intent_type
        }
    except Exception as e:
        logger.error(f"Ошибка классификации: {e}")
        return {
            "query_intent": {
                "intent_type": "unknown",
                "requires_analytics": False,
                "data_volume_estimate": "unknown"
            }
        }


def execute_sql_query(sql_query: str):
    """Выполняет SQL запрос и возвращает результат"""
    try:
        engine = create_engine('postgresql://postgres:1111@localhost:5433/fastapp')

        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            columns = result.keys()
            rows = result.fetchall()
            data = [dict(zip(columns, row)) for row in rows]
            df = pd.DataFrame(data)

        return {
            "success": True,
            "data": data,
            "dataframe": df,
            "row_count": len(data),
            "columns": list(columns)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def sql_generate_node(state: AgentState):
    """Узел генерации SQL запроса"""
    user_input = state.current_user_input
    intent = state.query_intent or {}

    try:
        structure_store = vector_manager.get_vector_store('structure')
        sql_info_scheme = structure_store.similarity_search(user_input)
        print(f"📚 Найдено {len(sql_info_scheme)} релевантных таблиц")

        schema_info = ""
        for doc in sql_info_scheme:
            table_name = doc.metadata.get('table_name', 'unknown')
            schema_info += f"Таблица: {table_name}\n"
            schema_info += f"Описание: {doc.page_content}\n\n"

        # Выбираем агента в зависимости от намерения и объема данных
        if intent.get('requires_analytics') and intent.get('data_volume_estimate') in ['large', 'medium']:
            print("🔄 Использую оптимизированный SQL агент для аналитики")
            result = agent_optimized_sql.invoke(
                input={"messages": [HumanMessage(content=user_input)]},
                config={"configurable": {"thread_id": 'optimized_sql_session'}},
                context={
                    "sql_structure": schema_info,
                    "user_intent": intent
                }
            )
            sql_query = result['structured_response'].sql_query
            print(f"📝 Оптимизированный SQL: {sql_query}")
        else:
            print("🔄 Использую стандартный SQL агент")
            result = agent_generate_sql.invoke(
                input={"messages": [HumanMessage(content=user_input)]},
                config={"configurable": {"thread_id": 'sql_generate_session'}},
                context={"sql_structure": schema_info}
            )
            sql_query = result['structured_response'].sql_query
            print(f"📝 Сгенерированный SQL: {sql_query}")

        # Выполняем SQL запрос
        execution_result = execute_sql_query(sql_query)
        print(execution_result)

        if not execution_result["success"]:
            error_msg = f"Ошибка выполнения SQL: {execution_result['error']}"
            return {
                "messages": [AIMessage(content=error_msg)],
                "sql_query": sql_query
            }

        # Определяем объем данных
        row_count = execution_result["row_count"]
        if row_count < 100:
            data_volume = "small"
        elif row_count < 1000:
            data_volume = "medium"
        else:
            data_volume = "large"

        print(f"📊 Получено строк: {row_count} (объем: {data_volume})")

        return {
            "messages": [AIMessage(content=f'Я нашел данные по вашему запросу. Обрабатываю...')],
            "sql_query": sql_query,
            "data_summary": execution_result['data'],
            "data_volume": data_volume
        }

    except Exception as e:
        logger.error(f"Ошибка генерации SQL: {e}")
        error_message = AIMessage(content="Извините, произошла ошибка при формировании запроса.")
        return {
            "messages": [error_message]
        }


def analytics_data_summary_node(state: AgentState):
    """Узел аналитики данных"""
    user_input = state.current_user_input
    data_summary = state.data_summary
    data_volume = state.data_volume
    intent = state.query_intent or {}

    print('🤔 Анализирую, что делать с данными...')

    try:
        # Если пользователь просит только данные и их не слишком много
        if not intent.get('requires_analytics', False):
            print("📋 Пользователь запросил только данные, аналитика не требуется")

            # Форматируем данные для вывода
            if data_volume == "large":
                # Для больших объемов показываем только первые 20 строк и статистику
                preview = data_summary[:20]
                total = len(data_summary)
                response = f"Найдено записей: {total}\n\n"
                response += "Первые 20 записей:\n"
                for i, row in enumerate(preview, 1):
                    response += f"{i}. {row}\n"
                response += f"\n... и еще {total - 20} записей"
            else:
                # Для небольших объемов показываем всё
                response = "Найденные данные:\n"
                for i, row in enumerate(data_summary, 1):
                    response += f"{i}. {row}\n"

            return {
                "messages": [AIMessage(content=response)],
            }

        # Если нужна аналитика
        print("📊 Требуется аналитическая обработка")

        # Подготавливаем данные для аналитики
        if data_volume == "large":
            # Для больших объемов делаем предварительную агрегацию
            df = pd.DataFrame(data_summary)
            summary_stats = df.describe().to_string() if not df.empty else "Нет данных для анализа"
            preview = data_summary[:20]

            analytics_data = f"""
            Краткая статистика:
            {summary_stats}

            Всего записей: {len(data_summary)}

            Примеры данных (первые 20):
            {preview}
            """
        else:
            # Для малых/средних объемов используем все данные
            analytics_data = str(data_summary)

        print(analytics_data)
        # Отправляем в аналитический агент
        result = agent_deep_talking.invoke(
            input={"messages": [
                SystemMessage(content=f"""
                Проведи анализ данных по запросу пользователя. ЭТО РЕАЛЬНЫЕ ДАННЫЕ

                Данные: {analytics_data}
                """)
            ]},
            config={"configurable": {"thread_id": 'analytic_session'}},
            context={
                "sql_result": analytics_data,
                "user_question": user_input,
                "intent_type": "analytics"
            }
        )

        return {
            "messages": [AIMessage(content=result['messages'][-1].content)],
        }

    except Exception as e:
        logger.error(f"Ошибка анализа: {e}")
        error_message = AIMessage(content="Извините, произошла ошибка при анализе данных.")
        return {
            "messages": [error_message]
        }