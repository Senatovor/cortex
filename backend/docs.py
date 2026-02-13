class DocBuilder:
    def __init__(self, summary: str = ""):
        self._data = {"summary": summary}
        # Стандартные описания статусов
        self._status_descriptions = {
            200: "Успешно",
            201: "Создано",
            202: "Принято",
            204: "Нет содержимого",
            400: "Неверный запрос",
            401: "Не авторизован",
            403: "Доступ запрещен",
            404: "Не найдено",
            409: "Конфликт",
            422: "Ошибка валидации",
            429: "Слишком много запросов",
            500: "Внутренняя ошибка сервера",
            502: "Ошибка шлюза",
            503: "Сервис недоступен",
        }

    def name(self, name: str) -> 'DocBuilder':
        self._data["name"] = name
        return self

    def description(self, desc: str) -> 'DocBuilder':
        self._data["description"] = desc
        return self

    def tag(self, tag_name: str) -> 'DocBuilder':
        self._data.setdefault("tags", []).append(tag_name)
        return self

    def response(self, status_code: int, description: str = None) -> 'DocBuilder':
        """Добавить ответ с автоматическим описанием"""
        # Поддержка передачи исключений
        if hasattr(status_code, 'status_code'):
            # Если передан объект исключения (например, HttpTokenMissingException)
            exception = status_code
            status_code = exception.status_code
            description = exception.detail

        if description is None:
            description = self._status_descriptions.get(
                status_code,
                f"Статус {status_code}"
            )

        self._data.setdefault("responses", {})[status_code] = {
            "description": description
        }
        return self

    def responses(self, *status_codes) -> 'DocBuilder':
        """Добавить несколько ответов сразу (поддерживает коды статусов и исключения)"""
        for status_code in status_codes:
            self.response(status_code)
        return self

    def build(self) -> dict:
        return self._data.copy()
