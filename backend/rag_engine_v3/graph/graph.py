from langchain_core.runnables import RunnableConfig
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver
import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.rag_engine.qdrant import vector_manager
from backend.rag_engine_v3.graph.state import GraphState
from backend.rag_engine_v3.graph.nodes import Nodes
from backend.rag_engine_v3.graph.conditions import Conditions
from backend.database.session import session_manager

asyncio.run(session_manager.init())


class AIGraphDatabase(Nodes, Conditions):
    def __init__(self, checkpointer: Any):
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
            'sql_analytic',
            self.check_size_df,
            {
                'need_optimize': 'sql_analytic',
                'not_need_optimize': 'analytic'
            }
        )
        self.graph.add_edge('analytic', END)

        self.ai_graph_database = self.graph.compile(checkpointer=checkpointer)

    async def call(self, input: str, id_session: str, db_session: AsyncSession, vector_manager) -> str:
        result = await self.ai_graph_database.ainvoke(
            GraphState(
                current_user_input=input
            ).model_dump(),
            config={
                'configurable': {
                    'vector_manager': vector_manager,
                    'db_session': db_session,
                    'thread_id': id_session
                }
            }
        )
        return result['messages'][-1].content
