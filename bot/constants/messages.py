from bot.schemas import UserProfile

class StartMessages:
    @staticmethod
    def hello_auth_user(user_profile: UserProfile) -> str:
        return f"Привет {user_profile.name}"