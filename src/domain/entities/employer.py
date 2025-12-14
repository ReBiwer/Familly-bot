from src.domain.entities.base import BaseEntity


class EmployerEntity(BaseEntity):
    hh_id: str
    name: str
    description: str

    def __str__(self):
        return f"Название компании: {self.name}\nОписание компании: {self.description}"
