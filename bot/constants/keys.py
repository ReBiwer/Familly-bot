class StorageKeys:
    """Ключи для хранения данных пользователя в FSM storage."""

    # Информация о пользователе HH
    USER_INFO = "user_data"
    AI_RESPONSE = "ai_response"


class CallbackKeys:
    """Ключи для хранения значений для вызова callback команд"""

    LOGIN = "login"
    PROFILE = "profile"
    LOGOUT = "logout"
    REGENERATE_AI_RESPONSE = "regenerate_response"
    SEND_AI_RESPONSE = "send"
