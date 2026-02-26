from typing import Any
from langchain.tools import tool
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, OperationalError, DataError
import os
import pandas as pd
from datetime import datetime

from .prompts import vector_manager


@tool
def get_info_database_from_vector_store(user_input: str) -> str:
    """Получение информации о таблицах в БД с их описанием в зависимости от запроса пользователя

    Args:
        user_input (str): запрос пользователя для поиска релевантных таблиц
    """
    print('Использую инструмент векторов...')
    try:
        structure_store = vector_manager.get_vector_store('structure')
        sql_info_scheme = structure_store.similarity_search(user_input)
        print(f"Найдено {len(sql_info_scheme)} релевантных таблиц")

        if not sql_info_scheme:
            return "Не найдено релевантных таблиц по вашему запросу. Попробуйте переформулировать запрос."

        schema_info = ""
        for doc in sql_info_scheme:
            table_name = doc.metadata.get('table_name', 'unknown')
            schema_info += f"Таблица: {table_name}\n"
            schema_info += f"Описание: {doc.page_content}\n\n"
        return schema_info
    except Exception as e:
        error_msg = f"Ошибка при получении информации из векторного хранилища: {str(e)}"
        print(error_msg)
        return error_msg


@tool
def execute_sql_query_to_csv(sql_query: str) -> dict[str, Any]:
    """Выполняет SQL запрос и сохраняет результат в CSV файл в корне проекта /files/csv

    Args:
        sql_query (str): SQL запрос для выполнения

    Returns:
        dict: Информация о результате выполнения и пути к сохраненному файлу
    """
    print('Использую инструмент выполнения запроса CSV...')
    print(f"Выполняю запрос: {sql_query}")

    try:
        engine = create_engine('postgresql://postgres:1111@localhost:5433/fastapp')
        with engine.connect() as conn:
            df = pd.read_sql_query(sql_query, conn)

        print(f"Запрос выполнен успешно, получено {len(df)} записей")

        csv_dir = os.path.join(os.getcwd(), 'files', 'csv')
        os.makedirs(csv_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"query_result_{timestamp}.xlsx"
        filepath = os.path.join(csv_dir, filename)

        df.to_excel(filepath, index=False)

        print(f"💾 Результат сохранен в файл: {filepath}")

        return {
            "success": True,
            "message": 'Запрос выполнен и его результат записан в Excel файл',
            "file_path": filepath,
            "row_count": len(df),
            "columns": df.columns.tolist(),
            "sql_query": sql_query
        }

    except ProgrammingError as e:
        error_msg = str(e)
        print(f"Ошибка синтаксиса SQL: {error_msg}")
        if "relation" in error_msg and "does not exist" in error_msg:
            suggestion = "Проверьте название таблицы. Возможно, таблица называется иначе или нужно использовать схему."
        elif "column" in error_msg and "does not exist" in error_msg:
            suggestion = "Проверьте названия колонок. Используйте информацию из векторного хранилища для правильных названий."
        elif "syntax error" in error_msg.lower():
            suggestion = "Исправьте синтаксис SQL запроса. Проверьте ключевые слова и пунктуацию."
        else:
            suggestion = "Проверьте структуру запроса и названия таблиц/колонок."

        return {
            "success": False,
            "error": f"ОШИБКА СИНТАКСИСА SQL: {error_msg}",
            "sql_query": sql_query,
            "error_type": "syntax_error",
            "suggestion": suggestion
        }

    except OperationalError as e:
        error_msg = str(e)
        print(f"Операционная ошибка БД: {error_msg}")
        return {
            "success": False,
            "error": f"ОШИБКА ПОДКЛЮЧЕНИЯ К БД: {error_msg}",
            "sql_query": sql_query,
            "error_type": "connection_error",
            "suggestion": "Проверьте подключение к базе данных или повторите запрос позже."
        }

    except DataError as e:
        error_msg = str(e)
        print(f"Ошибка типов данных: {error_msg}")
        return {
            "success": False,
            "error": f"ОШИБКА ТИПОВ ДАННЫХ: {error_msg}",
            "sql_query": sql_query,
            "error_type": "data_error",
            "suggestion": "Проверьте соответствие типов данных в запросе. Возможно, нужно преобразование типов."
        }

    except Exception as e:
        print(f"Непредвиденная ошибка: {str(e)}")
        return {
            "success": False,
            "error": f"НЕПРЕДВИДЕННАЯ ОШИБКА: {str(e)}",
            "sql_query": sql_query,
            "error_type": "unexpected_error",
            "suggestion": "Попробуйте упростить запрос или разбить его на части."
        }


@tool
def execute_sql_query_to_analytic(sql_query: str) -> dict[str, Any]:
    """Выполняет оптимизированный SQL запрос и возвращает результат

    Args:
        sql_query (str): SQL запрос для выполнения
    """
    print('Использую инструмент выполнения запроса аналитики...')
    print(f"Выполняю запрос: {sql_query}")

    try:
        engine = create_engine('postgresql://postgres:1111@localhost:5433/fastapp')

        with engine.connect() as conn:

            result = conn.execute(text(sql_query))
            columns = result.keys()
            rows = result.fetchall()

            if len(rows) > 1000:
                print(f"Предупреждение: получено {len(rows)} записей. Рекомендуется добавить LIMIT или агрегацию.")

            data = [dict(zip(columns, row)) for row in rows]

        print(f"Запрос выполнен успешно, получено {len(data)} записей")

        return {
            "success": True,
            "data": data[:100],
            "total_rows": len(data),
            "columns": list(columns),
            "sql_query": sql_query,
            "warning": "Показаны первые 100 записей" if len(data) > 100 else None
        }

    except ProgrammingError as e:
        error_msg = str(e)
        print(f"Ошибка синтаксиса SQL: {error_msg}")

        if "relation" in error_msg and "does not exist" in error_msg:
            suggestion = "Проверьте название таблицы. Используйте get_info_database_from_vector_store для получения правильных названий."
        elif "column" in error_msg and "does not exist" in error_msg:
            suggestion = "Проверьте названия колонок. Убедитесь, что они существуют в таблице."
        else:
            suggestion = "Исправьте синтаксис SQL запроса."

        return {
            "success": False,
            "error": f"ОШИБКА SQL: {error_msg}",
            "sql_query": sql_query,
            "error_type": "sql_error",
            "suggestion": suggestion
        }

    except Exception as e:
        print(f"Ошибка выполнения запроса: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "sql_query": sql_query,
            "error_type": "unknown_error",
            "suggestion": "Проанализируйте ошибку и исправьте запрос."
        }
