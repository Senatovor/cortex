from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger
import asyncio

from backend.rag_engine.qdrant import vector_manager
from backend.rag_engine_v3.rag_schemes import AgentState
from backend.rag_engine_v3.nodes import (
    analytic_node,
    check_size_df,
    sql_analytic_node,
    statisitc_node,
    user_input_node,
    check_to_end,
    classify_intent_node,
    data_node,
    check_to_retrie,
    classify_routing
)
from backend.database.session import session_manager

asyncio.run(session_manager.init())

# Создание графа
graph = StateGraph(AgentState)

# Добавление узлов
graph.add_node('user_input', user_input_node)
graph.add_node('classify_intent', classify_intent_node)
graph.add_node('data', data_node)
graph.add_node('statisitc', statisitc_node)
graph.add_node('sql_analytic', sql_analytic_node)
graph.add_node('analytic', analytic_node)

# Определение связей
graph.add_edge(START, "user_input")
graph.add_conditional_edges(
    "user_input",
    check_to_end,
    {
        'continue': 'classify_intent',
        'end': END
    }
)
graph.add_conditional_edges(
    'classify_intent',
    classify_routing,
    {
        "data" : 'data',
        'statistics': 'statisitc',
        'analytics': 'sql_analytic',
        "other": END
    }
)
graph.add_conditional_edges(
    'data',
    check_to_retrie,
    {
        "retrie": 'data',
        'continue': END
    }
)
graph.add_conditional_edges(
    'sql_analytic',
    check_to_retrie,
    {
        "retrie": 'sql_analytic',
        'continue': 'analytic'
    }
)
graph.add_conditional_edges(
    'sql_analytic',
    check_size_df,
    {
        'need_optimize': 'sql_analytic',
        'not_need_optimize': 'analytic'
    }
)
graph.add_edge('analytic', END)

if __name__ == "__main__":
    # Компилируем граф
    app = graph.compile(checkpointer=InMemorySaver())

    print("=" * 60)
    print("🤖 БОТ ДЛЯ РАБОТЫ С ДАННЫМИ И СТАТИСТИКОЙ".center(60))
    print("=" * 60)
    print("\n🎯 Возможности бота:")
    print("   • Получение данных (без ограничений)")
    print("   • Статистические расчеты (среднее, дисперсия, корреляция)")
    print("   • Анализ тенденций и динамики")
    print("\n📝 Команды:")
    print("   • 'выход', 'exit', 'quit', 'q' - завершение работы")
    print("   • 'debug on' - включить отладочную информацию")
    print("   • 'debug off' - выключить отладочную информацию")
    print("-" * 60)

    # Флаг для отладки
    debug_mode = False

    while True:
        try:
            user_text = input("\n👤 Вы: ").strip()

            # Обработка команд
            if user_text.lower() in ["выход", "exit", "quit", "q"]:
                print("\n👋 Программа завершена. До свидания!")
                break

            if user_text.lower() == "debug on":
                debug_mode = True
                print("🔧 Отладочный режим ВКЛЮЧЕН")
                continue

            if user_text.lower() == "debug off":
                debug_mode = False
                print("🔧 Отладочный режим ВЫКЛЮЧЕН")
                continue

            if not user_text:
                print("⚠️ Пожалуйста, введите запрос")
                continue

            print(f"\n🚀 Обрабатываю запрос: '{user_text}'")
            print("⏳ Ожидайте ответа...")
            print("-" * 50)
            
            db_session = None
            

            # Выполняем запрос к графу
            result = app.invoke(
                {
                    "current_user_input": user_text,
                    "messages": [],
                    "message_type": "",
                    "sql_query": "",
                    "error": None,
                    "error_attempt": 0
                },
            config={
                "configurable": {
                    "vector_manager": vector_manager,
                    "db_session": db_session
                    "thread_id": "some_thread_id"
                }
            }
            )

            # Получаем ответ агента
            if result.get("messages"):
                last_msg = result["messages"][-1]
                
                print("\n📊 ОТВЕТ АГЕНТА:")
                print("-" * 50)
                print(last_msg.content)
                print("-" * 50)

                # Отладочная информация
                if debug_mode:
                    print("\n🔍 Отладочная информация:")
                    print(f"📝 Тип намерения: {result.get('message_type', 'не определен')}")
                    
                    if result.get("sql_query"):
                        print(f"💾 SQL запрос:")
                        print("-" * 30)
                        print(result["sql_query"])
                        print("-" * 30)
                    
                    if result.get("error"):
                        print(f"❌ Ошибка: {result['error']}")
                        print(f"🔄 Попыток: {result.get('error_attempt', 0)}")
                    
                    print(f"📨 Всего сообщений: {len(result['messages'])}")
                    
                    # Показываем промежуточные шаги агента
                    if len(result['messages']) > 1:
                        print("\n📋 Промежуточные шаги:")
                        for i, msg in enumerate(result['messages'][:-1]):
                            if hasattr(msg, 'content') and msg.content:
                                preview = msg.content[:150] + "..." if len(msg.content) > 150 else msg.content
                                print(f"  Шаг {i + 1}: {preview}")
            else:
                print("❌ Не получен ответ от агента")

        except KeyboardInterrupt:
            print("\n\n⚠️ Работа прервана пользователем")
            break
        except Exception as e:
            print(f"\n❌ Ошибка при выполнении запроса: {str(e)}")
            if debug_mode:
                import traceback
                traceback.print_exc()
            else:
                print("   Для просмотра деталей включите debug mode")

        print("\n" + "=" * 60)
        print("✅ Готов к следующему запросу...")