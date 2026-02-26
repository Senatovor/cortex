from loguru import logger

from backend.rag_engine_v3.graph.state import GraphState


class Conditions:
    @staticmethod
    async def check_len_context_chat(state: GraphState) -> str:
        if state.messages_length >= 45:
            logger.info('Контекст переполнен, закрываю чат')
            return 'end'
        return 'continue'

    @staticmethod
    async def classify_routing(state: GraphState) -> str:
        classify = state.message_type
        if classify == 'data':
            return 'data'
        elif classify == 'statistics':
            return 'statistics'
        elif classify == 'analytics':
            return 'analytics'
        else:
            return 'other'

    @staticmethod
    def check_to_repeat_sql_generate(state: GraphState):
        if state.error_str:
            return 'repeat'
        return 'continue'

    @staticmethod
    def check_size_df(state: GraphState):
        if state.df_len >= 500:
            state.need_to_optimize = True
            return 'need_optimize'
        state.need_to_optimize = False
        return 'not_need_optimize'
