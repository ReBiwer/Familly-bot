from bot.schemas import UserProfile


class CommonMessages:
    @staticmethod
    def start_message(user_profile: UserProfile) -> str:
        return f"Привет {user_profile.name}"

    @staticmethod
    def profile_message(user_profile: UserProfile) -> str:
        return (
            f"Ваш профиль\n"
            f"Имя: {user_profile.name}\n"
            f"Отчество: {user_profile.mid_name}\n"
            f"Фамилия: {user_profile.last_name}\n"
            f"Телефон: {user_profile.phone}\n"
            f"Почта: {user_profile.email}"
        )

    @staticmethod
    def not_auth_user() -> str:
        return "Для продолжения, авторизуйтесь. Выполните команду /start"

    @staticmethod
    def help_message() -> str:
        return "Сообщение /help"
