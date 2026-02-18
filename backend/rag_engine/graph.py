from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger
import asyncio

from backend.rag_engine.qdrant import vector_manager
from backend.rag_engine.rag_scheme import AgentState
from backend.rag_engine.nodes import (
    sql_generate_node,
    user_input,
    check_to_end,
    analytics_data_summary_node,
    classify_intent_node  # Новый узел
)

asyncio.run(vector_manager.init())

# Создание графа
graph = StateGraph(AgentState)

# Добавление узлов
graph.add_node('user_input', user_input)
graph.add_node('classify_intent', classify_intent_node)  # Новый узел классификации
graph.add_node('analyze_sql', sql_generate_node)
graph.add_node('analytics_data_summary', analytics_data_summary_node)

# Определение связей
graph.add_edge(START, "user_input")
graph.add_conditional_edges(
    "user_input",
    check_to_end,
    {
        'continue': 'classify_intent',  # Теперь идем к классификации
        'end': END
    }
)
graph.add_edge('classify_intent', 'analyze_sql')
graph.add_edge('analyze_sql', 'analytics_data_summary')
graph.add_edge('analytics_data_summary', END)

if __name__ == "__main__":
    app = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "graph_session"}}

    print("🤖 Бот готов! (введите 'выход' для завершения)")
    print("🎯 Теперь я понимаю, когда нужны только данные, а когда аналитика!")

    while True:
        try:
            user_text = input("\n👤 Вы: ").strip()
            if user_text.lower() in ["выход", "exit", "quit"]:
                break

            result = app.invoke(
                {
                    "current_user_input": user_text,
                    "messages": [],
                    "message_type": "",
                    "sql_query": "",
                    "data_summary": [],
                    "query_intent": None,
                    "data_volume": None,
                    "processed_data": None
                },
                config=config
            )

            if result.get("messages"):
                last_msg = result["messages"][-1]
                print(f"🤖 ИИ: {last_msg.content}")

        except KeyboardInterrupt:
            print("\n⚠️ Работа прервана")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")