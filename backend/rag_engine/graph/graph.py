from langgraph.constants import START, END
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph
from typing import Any

from .state import GraphState
from .nodes import Nodes
from .conditions import Conditions


class AIGraphDatabase(Nodes, Conditions):
    def __init__(self, checkpointer: Any):
        super().__init__()
        
        self.graph = StateGraph(GraphState)

        self.graph.add_node('user_input', self.user_input_node)
        self.graph.add_node('classify_intent', self.classify_intent_node)
        self.graph.add_node('data', self.data_node)
        self.graph.add_node('statistics', self.statistics_node)
        self.graph.add_node('generate_sql_for_analytic', self.generate_sql_analytic_node)
        self.graph.add_node('analytic', self.analytic_node)

        self.graph.add_edge(START, 'user_input')
        self.graph.add_conditional_edges(
            'user_input',
            self.check_len_context_chat,
            {
                'continue': 'classify_intent',
                'end': END
            }
        )
        self.graph.add_conditional_edges(
            'classify_intent',
            self.classify_routing,
            {
                'data': 'data',
                'statistics': 'statistics',
                'analytics': 'generate_sql_for_analytic',
                'other': END
            }
        )
        self.graph.add_conditional_edges(
            'data',
            self.check_to_repeat_sql_generate,
            {
                'repeat': 'data',
                'continue': END
            }
        )
        self.graph.add_conditional_edges(
            'statistics',
            self.check_to_repeat_sql_generate,
            {
                'repeat': 'statistics',
                'continue': END
            }
        )
        self.graph.add_conditional_edges(
            'generate_sql_for_analytic',
            self.check_to_repeat_sql_generate,
            {
                'repeat': 'generate_sql_for_analytic',
                'continue': 'analytic'
            }
        )
        self.graph.add_conditional_edges(
            'generate_sql_for_analytic',
            self.check_size_df,
            {
                'need_optimize': 'generate_sql_for_analytic',
                'not_need_optimize': 'analytic'
            }
        )
        self.graph.add_edge('analytic', END)

        self.ai_graph_database = self.graph.compile(checkpointer=checkpointer)

    async def call(self, input: str, id_session: str, db_session: AsyncSession, vector_manager) -> str:
        result = await self.ai_graph_database.ainvoke(
            GraphState(
                current_user_input=input
            ).model_dump(), # type: ignore
            config={
                'configurable': {
                    'vector_manager': vector_manager,
                    'db_session': db_session,
                    'thread_id': id_session
                }
            }
        )
        return result['messages'][-1].content

from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
ai_graph = AIGraphDatabase(checkpointer=checkpointer)

# @session_manager.connection()
# async def chat_with_ai(db_session):
    
#     checkpointer = InMemorySaver()
#     ai_graph = AIGraphDatabase(checkpointer=checkpointer)
    
#     print("🤖 Чат с AI Graph Database запущен!")
#     print("Введите 'exit' для выхода\n")
    
#     id_session = "user_123"  # Можно генерировать уникальный ID для каждого пользователя
    
#     while True:
#         # Получаем ввод пользователя
#         user_input = input("👤 Вы: ").strip()
        
#         # Проверка на выход
#         if user_input.lower() in ['exit', 'quit', 'выход']:
#             print("🤖 До свидания!")
#             break
        
#         if not user_input:
#             continue
        
#         try:
#             # Вызываем метод call
#             response = await ai_graph.call(
#                 input=user_input,
#                 id_session=id_session,
#                 db_session=db_session,  # Подставьте вашу сессию
#                 vector_manager=vector_manager  # Подставьте ваш векторный менеджер
#             )
            
#             # Выводим ответ
#             print(f"🤖 AI: {response}")
            
#         except Exception as e:
#             print(f"❌ Ошибка: {e}")
#             print("Попробуйте еще раз...")

# # Функция для запуска асинхронного чата
# def run_chat():
#     asyncio.run(chat_with_ai())

# if __name__ == "__main__":
#     run_chat()
