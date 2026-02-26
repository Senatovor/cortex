from ..rag_engine.qdrant import VectorStoreManager


async def get_schema_db_info(input: str, vector_manager: VectorStoreManager) -> str | None:
    structure_store = vector_manager.get_vector_store('structure')
    sql_info_scheme = await structure_store.asimilarity_search(input)
    print(f"Найдено {len(sql_info_scheme)} релевантных таблиц")
    if not sql_info_scheme:
        return None
    schema_info = ""
    for doc in sql_info_scheme:
        table_name = doc.metadata.get('table_name', 'unknown')
        schema_info += f"Таблица: {table_name}\n"
        schema_info += f"Описание: {doc.page_content}\n\n"
    return schema_info
