from langchain_ollama import ChatOllama
from backend.config import config

model = ChatOllama(
    model=config.rag_config.MODEL_NAME,
    base_url=config.rag_config.MODEL_HOST,
    temperature=config.rag_config.TEMPERATURE,
)

response = model.invoke([{"role": "user", "content": "Кто тебя создал?"}])

print(f"Тип ответа: {type(response)}")
print(f"Содержимое: {response.content}")
