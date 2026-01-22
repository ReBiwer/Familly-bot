from pydantic import BaseModel, ConfigDict, Field


class DefaultAgentRequest(BaseModel):
    user_id: int = Field(..., description="Telegram ID пользователя")
    message: str = Field(..., min_length=1, max_length=4000, description="Текст сообщения")

    model_config = ConfigDict(from_attributes=True)


class DefaultAgentResponse(BaseModel):
    user_id: int
    message: str
    response: str

    model_config = ConfigDict(from_attributes=True)
