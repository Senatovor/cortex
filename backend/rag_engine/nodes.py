from loguru import logger
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from .agent import agent, model
from .prompts import classification_prompt, classification_parser, sql_prompt, sql_parser
from .qdrant import vector_manager
from .rag_scheme import AgentState


def user_input(state: AgentState):
    """Теперь этот узел просто пропускает ввод, который пришел извне"""
    # Ничего не делаем, ввод уже в state.current_user_input
    # Можно добавить сообщение в историю здесь, если нужно
    return {
        "messages": [HumanMessage(content=state.current_user_input)]
    }


def check_to_end(state: AgentState):
    """Проверка лимита истории"""
    # Считаем только диалог (Human + AI), игнорируя системные сообщения
    dialog_messages = [m for m in state.messages if isinstance(m, (HumanMessage, AIMessage))]

    if len(dialog_messages) >= 7:
        logger.info('Контекст переполнен, пора заканчивать')
        return 'end'
    logger.info(f'Продолжаем... (сообщений: {len(dialog_messages)})')
    return 'continue'


def classify_message_node(state: AgentState):
    """Узел принятия сообщения и классификации сообщения"""
    new_state = {
        "current_user_input": state.current_user_input
    }
    try:
        logger.info(f"Определяю тип сообщения для: {state.current_user_input}...")
        classification_chain = classification_prompt | model | classification_parser
        result = classification_chain.invoke({"user_input": state.current_user_input})
        message_type = result["message_type"]
        confidence = result["confidence"]
        logger.info(f"Тип: {message_type} (уверенность: {confidence:.2f})")
        new_state["message_type"] = message_type
    except Exception as e:
        logger.info(f"Ошибка классификации: {e}")
        new_state["message_type"] = "question"
    return new_state


def answer_question_node(state: AgentState):
    user_input = state.current_user_input
    try:
        logger.info("Отвечаю на вопрос...")

        # Передаём HumanMessage агенту для контекста
        result = agent.invoke({
            "messages": state.messages + [HumanMessage(content=user_input)]
        })

        all_messages = result["messages"]
        ai_response = all_messages[-1]
        logger.info(f"ИИ: {ai_response.content}")

        # 🔧 Возвращаем ОБА: вопрос пользователя + ответ ИИ
        return {
            "messages": [ai_response]
        }
    except Exception as e:
        logger.error(f"Ошибка при ответе: {e}")
        error_message = AIMessage(content="Извините, произошла ошибка при обработке вашего вопроса.")
        return {
            "messages": [error_message]
        }


def analyze_sql_node(state: AgentState):
    """Узел анализа ГИА"""
    user_input = state.current_user_input
    try:
        logger.info("Создаю sql код...")

        sql_store = vector_manager.get_vector_store('sql')
        structure_store = vector_manager.get_vector_store('structure')

        sql_info_scheme = structure_store.similarity_search(user_input)
        sql_query_example = sql_store.similarity_search(user_input)

        logger.info(sql_info_scheme)
        logger.info(sql_query_example)

        analysis_chain = sql_prompt | model | sql_parser
        sql_result = analysis_chain.invoke(
            {
                "input_user": user_input,
                "sql_query_example": sql_query_example,
                "sql_info_scheme": sql_info_scheme,
            }
        )

        sql_query = sql_result.get("sql_query", "")
        response_text = f"Вот SQL запрос для вашего вопроса:\n\n```sql\n{sql_query}\n```"
        logger.info(response_text)

        # 🔧 Возвращаем ОБА сообщения + sql_query
        return {
            "messages": [
                AIMessage(content=response_text)
            ],
            "sql_query": sql_query
        }
    except Exception as e:
        logger.error(f"Ошибка анализа: {e}")
        error_message = AIMessage(content="Извините, произошла ошибка при анализе.")
        return {
            "messages": [
                error_message
            ]
        }


def route_after_classification(state: AgentState):
    """Маршрутизация после классификации"""
    message_type = state.message_type
    if message_type == "analytics":
        return "analyze_sql"
    else:
        return "answer_question"
