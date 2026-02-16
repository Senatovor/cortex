from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from .rag_scheme import MessageClassificationScheme, SQLScheme

classification_parser = JsonOutputParser(pydantic_object=MessageClassificationScheme)
classification_prompt = PromptTemplate(
    template="""Определи тип сообщения пользователя: аналитика (analytics) или обычный вопрос (question).

АНАЛИТИКА (analytics) - это запрос на анализ данных, поиск закономерностей, статистику, отчеты, агрегацию данных. 
Примеры аналитических запросов:
- "Покажи средний балл учеников по классам"
- "Сколько учеников сдали экзамен на отлично?"
- "Статистика успеваемости за последний год"
- "Получение информации об учениках и их оценках" - ЭТО АНАЛИТИКА, так как запрос на получение данных для анализа
- "Выведи список учеников с оценками"
- "Какая успеваемость в 9 классах?"

ВОПРОС (question) - это общий вопрос, запрос информации, объяснения, помощи, не связанный с анализом данных.
Примеры вопросов:
- "Как подготовиться к экзамену?"
- "Что такое ГИА?"
- "Привет, как дела?"
- "Расскажи о системе образования"

Сообщение пользователя: {user_input}

{format_instructions}

Верни ТОЛЬКО JSON!""",
    input_variables=["user_input"],
    partial_variables={"format_instructions": classification_parser.get_format_instructions()}
)

sql_parser = JsonOutputParser(pydantic_object=SQLScheme)
sql_prompt = PromptTemplate(
    template="""Напиши SQL код для получения данных ГИА из PostgreSQL

Запрос пользователя: {input_user}
Информация о полях в таблице: {sql_info_scheme}
Пример SQL кода: {sql_query_example}

{format_instructions}

Верни ТОЛЬКО JSON с полем sql_query!""",
    input_variables=["sql_info_scheme", "sql_query_example", "input_user"],
    partial_variables={"format_instructions": sql_parser.get_format_instructions()}
)
