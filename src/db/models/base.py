from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.functions import func


class BaseModel(DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

    def dump_dict(self) -> dict:
        """
        Метод для получения словаря с рекурсивным преобразованием сопутствующих сущностей
        """
        result_dict = {}
        for attr, value in self.__dict__.items():
            # если значение итерируемый объект, то проходим по каждому элементу
            if isinstance(value, list):
                converted_value = []
                # проходимся по всем значениям последовательности
                for val in value:
                    # если это экземпляр нашего же класса, то вызываем рекурсию
                    if isinstance(val, BaseModel):
                        converted_value.append(val.dump_dict())
                    else:
                        converted_value.append(val)
                result_dict[attr] = converted_value
                continue
            result_dict[attr] = value
        return result_dict
