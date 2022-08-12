class HTTPStatusError(Exception):
    """Исключение при проверка статуса запроса."""
    pass


class ServerError(Exception):
    """Исключение при работе сервера Яндекс Практикум. """
    pass


class CheckApiAnswerError(Exception):
    """Исключение при проверке данных."""
    pass


class ParseError(Exception):
    """Исключение при попытке обработки данных."""
    pass
