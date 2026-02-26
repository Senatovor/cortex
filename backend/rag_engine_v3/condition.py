from loguru import logger

from .rag_schemes import AgentState


async def check_len_context_chat(state: AgentState) -> str:
    if state.messages_length >= 45:
        print('Контекст переполнен, закрываю чат')
        return 'end'
    return 'continue'


async def classify_routing(state: AgentState) -> str:
    classify = state.message_type
    if classify == 'data':
        return 'data'
    elif classify == 'statistics':
        return 'statistics'
    elif classify == 'analytics':
        return 'analytics'
    else:
        return 'other'


def check_to_repeat_sql_generate(state: AgentState):
    if state.error_str:
        return 'repeat'
    return 'continue'


def check_size_df(state: AgentState):
    if state.df_len >= 500:
        state.need_to_optimize = True
        return 'need_optimize'
    state.need_to_optimize = False
    return 'not_need_optimize'
