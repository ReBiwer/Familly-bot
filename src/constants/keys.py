class StorageKeys:
    """Ключи для хранения данных пользователя в FSM storage."""

    # Информация о пользователе HH
    USER_INFO = "user_data"
    ACTIVE_RESUME_ID = "active_resume_id"
    ACTIVE_RESUME_TITLE = "active_resume_title"
    AI_RESPONSE = "ai_response"
    CURRENT_VACANCY_URL = "current_vacancy_url"
    CURRENT_VACANCY_HH_ID = "current_vacancy_hh_id"


class CallbackKeys:
    """Ключи для хранения значений для вызова callback команд"""

    LOGIN = "login"
    PROFILE = "profile"
    LOGOUT = "logout"
    REGENERATE_AI_RESPONSE = "regenerate_response"
    SEND_AI_RESPONSE = "send"
