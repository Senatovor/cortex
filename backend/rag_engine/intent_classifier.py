from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import config
from backend.rag_engine.rag_scheme import QueryIntentScheme
import json


class IntentClassifier:
    """Классификатор намерений пользователя"""

    def __init__(self):
        self.model = ChatOllama(
            model=config.rag_config.MODEL_NAME,
            base_url=config.rag_config.MODEL_HOST,
            temperature=0.1,  # Низкая температура для детерминированности
        )

    async def classify(self, user_input: str) -> QueryIntentScheme:
        """Определяет намерение пользователя"""

        system_prompt = """Ты - классификатор намерений для системы работы с базой данных.
        Определи, что хочет пользователь: просто получить данные или провести анализ.

        Правила классификации:
        - DATA_ONLY: пользователь просит "дай данные", "покажи", "выведи", "список", "таблицу", "поля"
        - ANALYTICS: пользователь просит "проанализируй", "сравни", "тенденция", "динамика", "статистика", "среднее", "максимум", "минимум", "итоги"

        Также оцени объем данных:
        - SMALL: запросы по конкретному ученику, классу, школе (до 100 строк)
        - MEDIUM: запросы по району, нескольким школам (100-1000 строк)
        - LARGE: запросы по всему региону, всем школам (более 1000 строк)

        Верни ответ в формате JSON.
        """

        prompt = f"""Запрос пользователя: "{user_input}"

        Определи:
        1. intent_type (data_only/analytics/unknown)
        2. requires_analytics (true/false)
        3. data_volume_estimate (small/medium/large/unknown)
        4. key_metrics (какие метрики важны для анализа)
        5. aggregation_needed (нужна ли агрегация)

        JSON ответ:"""

        try:
            response = self.model.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ])

            # Пытаемся извлечь JSON из ответа
            content = response.content
            # Очищаем от возможных markdown
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            intent_data = json.loads(content)
            return QueryIntentScheme(**intent_data)

        except Exception as e:
            print(f"Ошибка классификации: {e}")
            # Возвращаем безопасный дефолт
            return QueryIntentScheme(
                intent_type="unknown",
                requires_analytics=False,
                data_volume_estimate="unknown",
                aggregation_needed=False
            )


# Создаем глобальный экземпляр
intent_classifier = IntentClassifier()