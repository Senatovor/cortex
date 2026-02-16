from langgraph.constants import START, END
from langgraph.graph import StateGraph
from loguru import logger
import asyncio

from backend.rag_engine.agent import checkpointer
from backend.rag_engine.qdrant import vector_manager
from backend.rag_engine.rag_scheme import AgentState
from backend.rag_engine.nodes import (
    classify_message_node,
    answer_question_node,
    analyze_sql_node,
    route_after_classification,
    user_input,
    check_to_end
)

asyncio.run(vector_manager.init())


# Создание графа
graph = StateGraph(AgentState)

# Добавление узлов
graph.add_node('user_input', user_input)
graph.add_node('classify_message', classify_message_node)
graph.add_node('answer_question', answer_question_node)
graph.add_node('analyze_sql', analyze_sql_node)

# Определение связей
graph.add_edge(START, "user_input")
graph.add_conditional_edges(
    "user_input",
    check_to_end,
    {
        'continue': 'classify_message',
        'end': END
    }
)
graph.add_conditional_edges(
    "classify_message",
    route_after_classification,
    {
        "analyze_sql": "analyze_sql",
        "answer_question": "answer_question"
    }
)
graph.add_edge('analyze_sql', END)
graph.add_edge('answer_question', END)

if __name__ == "__main__":
    # Компиляция графа с чекпоинтером
    app = graph.compile(checkpointer=checkpointer)

    # Конфигурация сессии (thread_id хранит историю)
    config = {"configurable": {"thread_id": "user_123_session_1"}}

    print("🤖 Бот готов! (введите 'выход' для завершения)")

    while True:
        try:
            user_text = input("\n👤 Вы: ").strip()
            if user_text.lower() in ["выход", "exit", "quit"]:
                break

            # ✅ Правильная структура ввода
            result = app.invoke(
                {
                    "current_user_input": user_text,
                    "messages": [],
                    "message_type": "",
                    "sql_query": ""
                },
                config=config
            )

            # Вывод ответа
            if result.get("messages"):
                last_msg = result["messages"][-1]
                print(f"🤖 ИИ: {last_msg.content}")

        except KeyboardInterrupt:
            print("\n⚠️ Работа прервана")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
