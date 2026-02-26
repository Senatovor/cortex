from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent

from backend.config import config
from backend.rag_engine_v2.tools import get_info_database_from_vector_store, execute_sql_query_to_csv, execute_sql_query_to_analytic
from backend.rag_engine_v2.prompts import agent_analytic_prompt


def create_agent_analytic():
    model = ChatOllama(
        # model=config.rag_config.MODEL_NAME,
        model='qwen3:14b',
        base_url=config.rag_config.MODEL_HOST,
        temperature=config.rag_config.TEMPERATURE,
    )
    agent_analytic = create_agent(
        model=model,
        tools=[get_info_database_from_vector_store, execute_sql_query_to_csv, execute_sql_query_to_analytic],
        checkpointer=InMemorySaver(),
        system_prompt=agent_analytic_prompt
    )
    return agent_analytic


agent = create_agent_analytic()

print("📝 Введите 'exit' для выхода из программы")
print("-" * 50)

while True:
    request = input("\n💬 Введите ваш запрос: ")

    if request.lower() in ['exit', 'выход', 'quit', 'q']:
        print("👋 Программа завершена")
        break

    if not request.strip():
        print("⚠️ Пожалуйста, введите запрос")
        continue

    print(f"\n🚀 Выполняю запрос: '{request}'")
    print("⏳ Ожидайте ответа от агента...")
    print("-" * 50)

    try:
        # Выполняем запрос к агенту
        result = agent.invoke(
            input={"messages": [HumanMessage(content=request)]},
            config={"configurable": {"thread_id": 'sql_session'}},
        )

        # Получаем ответ агента
        agent_response = result['messages'][-1].content

        print("\n📊 ОТВЕТ АГЕНТА:")
        print("-" * 50)
        print(agent_response)
        print("-" * 50)

        # Дополнительная информация для отладки (опционально)
        show_debug = input("\n🔧 Показать отладочную информацию? (y/n): ").lower()
        if show_debug == 'y':
            print("\n🔍 Отладочная информация:")
            print(f"Количество сообщений в истории: {len(result['messages'])}")
            print(f"Тип финального сообщения: {type(result['messages'][-1])}")

            # Показываем все шаги агента (если есть промежуточные сообщения)
            if len(result['messages']) > 2:
                print("\n📋 Шаги агента:")
                for i, msg in enumerate(result['messages'][:-1]):
                    if hasattr(msg, 'content') and msg.content:
                        print(f"  Шаг {i + 1}: {msg.content[:100]}...")

    except Exception as e:
        print(f"❌ Ошибка при выполнении запроса: {str(e)}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 50)
    print("Готов к следующему запросу...")

print("\n✨ Тестирование завершено")

