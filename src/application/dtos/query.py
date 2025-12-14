from pydantic import Field
from src.application.dtos.base import BaseDTO


class QueryCreateDTO(BaseDTO):
    subject: str = Field(description="Уникальный идентификатор пользователя, в основном это hh_id")
    user_id: int
    url_vacancy: str = Field(default="https://usinsk.hh.ru/vacancy/125537679")
    resume_hh_id: str = Field(default="6044a353ff0f1126620039ed1f42324e494b4c")


class QueryRecreateDTO(QueryCreateDTO):
    response: str
    user_comments: str
