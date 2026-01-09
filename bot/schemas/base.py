from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Базовая схема с общими настройками.

    Настройки:
    - from_attributes=True — позволяет создавать схему из ORM модели
      Пример: UserRead.model_validate(user_orm_instance)

    - str_strip_whitespace=True — автоматически убирает пробелы в начале/конце строк
      Пример: "  Владимир  " -> "Владимир"
    """

    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
    )


class BaseReadSchema(BaseSchema):
    """
    Базовая схема для чтения данных.

    Включает поля, которые есть у всех сущностей в БД:
    - id: первичный ключ
    - created_at: дата создания
    """

    id: int
    created_at: datetime
