import logging
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel as PydanticBaseModel
from pydantic.fields import FieldInfo
from sqlalchemy import inspect, select
from src.application.repositories.base import ISQLRepository
from src.domain.entities.base import BaseEntity
from src.infrastructure.db.models.base import BaseModel

logger = logging.getLogger(__name__)


class SQLAlchemyRepository[ET: BaseEntity, DBModel: BaseModel](ISQLRepository[ET]):
    model_class: type[DBModel]
    entity_class: type[ET]

    def inspect_model(
        self,
        *,
        model_class: type[BaseModel] = None,
        excluded_class: type[BaseModel] | None = None,
        _visited: set[type[BaseModel]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Собирает структуру связей для ORM-модели (model_class переданный в атрибутах класса).

        Возвращает словарь вида:
        {
            "relation_name": {
                "module": "python module",
                "model": "ClassName",
                "direction": "ONETOMANY",
                "uselist": True,
                "relations": { ... рекурсивный результат ... }
            },
            ...
        }
        """
        if _visited:
            logger.debug("Entering recursion")
        logger.debug("Inspected model: %s", model_class)
        inspected_model_class = model_class if model_class else self.model_class
        mapper = inspect(inspected_model_class)
        visited = set() if _visited is None else set(_visited)
        visited.add(inspected_model_class)

        relations: dict[str, dict[str, Any]] = {}

        for rel_key, rel in sorted(mapper.relationships.items(), key=lambda item: item[0]):
            target_cls = rel.mapper.class_

            if excluded_class is not None and target_cls is excluded_class:
                continue

            if target_cls in visited:
                # Связь ведёт к классу, который уже присутствует в текущей ветке.
                # Пропускаем, чтобы не дублировать родителя/предка в выдаче.
                continue

            logger.debug("Collected info")
            relation_info: dict[str, Any] = {
                "module": target_cls.__module__,
                "model": target_cls,
                "direction": rel.direction.name,
                "uselist": rel.uselist,
                "relations": self.inspect_model(
                    model_class=target_cls,
                    excluded_class=excluded_class,
                    _visited=visited | {target_cls},
                ),
            }

            relations[rel_key] = relation_info
        logger.debug("Returned info")
        return relations

    def inspect_entity(
        self,
        *,
        entity_class: type[BaseEntity] = None,
        excluded_class: type[BaseEntity] | None = None,
        _visited: set[type[BaseEntity]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Собирает структуру связей для pydantic-модели (model_entity переданный в атрибутах класса).

        Возвращает словарь вида:
        {
            "relation_name": {
                "module": "python module",
                "model": "ClassName",
                "uselist": True,
                "relations": { ... рекурсивный результат ... }
            },
            ...
        }
        """
        if _visited:
            logger.debug("Entering recursion")
        logger.debug("Inspected entity: %s", entity_class)
        inspected_entity_class = entity_class if entity_class else self.entity_class
        visited = set() if _visited is None else set(_visited)
        visited.add(inspected_entity_class)

        relations: dict[str, dict[str, Any]] = {}

        def _unwrap(annotation: Any) -> Any:
            """
            Приводит аннотацию к базовому типу.

            Убирает Optional/Union, оставляя единственный не-None аргумент.
            Для сложных Union возвращает исходную аннотацию как есть.
            """
            origin = get_origin(annotation)
            if origin in {Union, UnionType}:
                args = [arg for arg in get_args(annotation) if arg is not type(None)]
                if len(args) == 1:
                    return _unwrap(args[0])
                return annotation
            return annotation

        def _extract_target(field_info: FieldInfo) -> tuple[type[Any], bool] | None:
            """
            Определяет целевой тип поля и признак коллекции.

            Возвращает кортеж (target_cls, is_collection) либо None,
            если поле нельзя рассматривать как связь.
            """
            annotation = _unwrap(field_info.annotation)
            origin = get_origin(annotation)

            # Коллекции (list, set, tuple) рассматриваем как множественные связи.
            if origin in {list, set, tuple}:
                args = get_args(annotation)
                if len(args) != 1:
                    return None
                target_annotation = _unwrap(args[0])
                if isinstance(target_annotation, type):
                    return target_annotation, True
                return None

            if isinstance(annotation, type):
                return annotation, False

            return None

        for field_name in sorted(inspected_entity_class.model_fields):
            field_info: FieldInfo = inspected_entity_class.model_fields[field_name]

            extracted = _extract_target(field_info)
            if extracted is None:
                continue

            target_cls, is_collection = extracted

            if not isinstance(target_cls, type):
                continue

            if not issubclass(target_cls, PydanticBaseModel):
                continue

            if excluded_class is not None and target_cls is excluded_class:
                continue

            if target_cls in visited:
                # Избегаем повторного добавления класса, который уже присутствует в ветке.
                continue

            logger.debug("Collected info")
            relation_info: dict[str, Any] = {
                "module": target_cls.__module__,
                "model": target_cls,
                "uselist": is_collection,
                "relations": {},
            }

            if issubclass(target_cls, BaseEntity):
                relation_info["relations"] = self.inspect_entity(
                    entity_class=target_cls,
                    excluded_class=excluded_class,
                    _visited=visited | {target_cls},
                )

            relations[field_name] = relation_info
        logger.debug("Returned info")
        return relations

    def get_nested_relations(
        self,
    ) -> dict[str, tuple[type[BaseModel], type[BaseEntity]]]:
        """
        Функция для получения словаря для маппинга ORM модели и BaseEntity сущности

        Возвращает словарь с общим ключ для BaseModel и BaseEntity
        """
        logger.debug(
            "Started collect nested relations to ORM model (%s) and entity (%s)",
            self.model_class,
            self.entity_class,
        )
        entity_inspect_dict = self.inspect_entity()
        model_inspect_dict = self.inspect_model()
        nested_dict = dict()

        def _collect_data(
            entity_dict: dict[str, dict[str, Any]],
            model_dict: dict[str, dict[str, Any]],
        ):
            logger.debug(
                "Collected data: model=%s, entity=%s",
                model_dict["model"],
                entity_dict["model"],
            )
            collect_dict = dict()
            for key_entity in entity_dict.keys():
                if key_entity in model_dict.keys():
                    collect_dict[key_entity] = (
                        model_dict[key_entity]["model"],
                        entity_dict[key_entity]["model"],
                    )
                if (
                    entity_dict[key_entity]["relations"] is not None
                    and model_dict[key_entity]["relations"] is not None
                ):
                    collect_dict.update(
                        _collect_data(
                            entity_dict[key_entity]["relations"],
                            model_dict[key_entity]["relations"],
                        )
                    )
            logger.debug("returned data")
            return collect_dict

        nested_dict.update(_collect_data(entity_inspect_dict, model_inspect_dict))
        logger.debug("End collect nested relations")
        return nested_dict

    def _update_nested_model(
        self,
        nested_entity: BaseEntity,
        key_nested_entity: str,
        nested_relations: dict[str, tuple[type[BaseModel], type[BaseEntity]]],
    ) -> BaseModel:
        # извлечение связи классов ORM модели и BaseEntity
        nested_model_cls, _ = nested_relations.pop(key_nested_entity)
        logger.debug("Updated nested model=%s", nested_model_cls)
        # словарь куда будет собираться все sub nested ORM модели
        nested_data_model = dict()
        # множество ключей, которые оказались sub nested ORM моделями
        dump_exclude_keys = set()

        for key, _field_info in nested_entity.__class__.model_fields.items():
            # если ключ есть во вложенных связях, значит берем этот атрибут в обработку
            if key in nested_relations:
                # добавляем этот ключ в исключения
                dump_exclude_keys.add(key)
                # получаем атрибут вложенной сущности (может быть просто другой сущностью или же списком сущностей)
                sub_nested_entity: BaseEntity | list[BaseEntity] = getattr(nested_entity, key)

                # если это список сущностей, то итерируемся по каждой и
                # рекурсивно получаем экземпляры соответствующих ORM моделей
                if isinstance(sub_nested_entity, list):
                    logger.debug("Entering recursion")
                    sub_nested_models = [
                        self._update_nested_model(sub_entity, key, nested_relations)
                        for sub_entity in sub_nested_entity
                    ]
                    # сохраняем в словарь с данными для конечной валидации модели
                    nested_data_model[key] = sub_nested_models
                # если атрибутом оказался экземпляр другой сущности,
                # то просто делаем dump и получаем экземпляр ORM модели
                else:
                    # получаем ORM модель соответствующей данной сущности
                    sub_nested_model_cls, _ = nested_relations[key]
                    sub_nested_model = sub_nested_model_cls(**sub_nested_entity.model_dump())
                    # сохраняем в словарь с данными для конечной валидации модели
                    nested_data_model[key] = sub_nested_model

        nested_data_model.update(nested_entity.model_dump(exclude=dump_exclude_keys))
        logger.debug("Returned updated nested model=%s", nested_model_cls)
        return nested_model_cls(**nested_data_model)

    def _validate_entity_to_db_model(self, data: ET) -> DBModel:
        """
        Метод для получения экземпляра ORM модели из BaseEntity
        со всеми вложенными связями с другими ORM моделями
        """
        # тут будет хранится вся информация для инстанса ORM модели
        logger.debug("Started validate entity=%s", self.entity_class)
        data_model_instance = dict()
        dump_exclude_keys = set()
        data_entity = data.model_dump()
        nested_relations = self.get_nested_relations()

        for key, value in data_entity.items():
            if not isinstance(value, list):
                if not isinstance(value, BaseEntity):
                    data_model_instance[key] = value
                else:
                    nested_model_data = getattr(data, key)
                    nested_model_cls, _ = nested_relations[key]
                    nested_model = nested_model_cls(**nested_model_data)
                    data_model_instance[key] = nested_model

            else:
                dump_exclude_keys.add(key)
                _, nested_entity_cls = nested_relations[key]
                nested_entity_instances = (
                    nested_entity_cls.model_validate(data_nested_entity)
                    for data_nested_entity in value
                )
                nested_entities = [
                    self._update_nested_model(nested_entity_inst, key, nested_relations)
                    for nested_entity_inst in nested_entity_instances
                ]
                data_model_instance[key] = nested_entities

        data_model_instance.update(data.model_dump(exclude=dump_exclude_keys))
        logger.debug("End validate entity=%s", self.entity_class)
        return self.model_class(**data_model_instance)

    async def _check_exist_entity(self, data: ET) -> DBModel | None:
        raise NotImplementedError

    async def get(self, **filters) -> ET | None:
        logger.debug("Selecting instance %s with filters=%s", self.model_class, filters)
        stmt = select(self.model_class).filter_by(**filters)
        result = await self.session.execute(stmt)
        model_instance = result.scalar_one_or_none()
        if model_instance:
            logger.debug("Return instance %s", self.model_class)
            return self.entity_class.model_validate(model_instance.dump_dict())
        logger.debug("Instance %s not found", self.model_class)
        return None

    async def create(self, entity: ET) -> ET:
        logger.debug(
            "Create instance ORM model %s from entity=%s",
            self.model_class,
            self.entity_class,
        )
        existing_instance = await self._check_exist_entity(entity)
        if existing_instance:
            logger.debug("Instance exist in DB, return data=%s", existing_instance)
            return self.entity_class.model_validate(existing_instance.dump_dict())

        model_instance = self._validate_entity_to_db_model(entity)
        logger.debug("Instance ORM model created")
        self.session.add(model_instance)
        await self.session.flush()
        logger.debug("Instance added to session")
        return self.entity_class.model_validate(model_instance.dump_dict())

    async def update(self, entity: ET) -> ET:
        if entity.id is None:
            logger.debug("Entity %s does not exist", entity)
            msg = f"Невозможно обновить {self.entity_class.__name__} без идентификатора"
            raise ValueError(msg)

        model_instance = self._validate_entity_to_db_model(entity)
        await self.session.flush()
        logger.debug("Instance added to session")
        return self.entity_class.model_validate(model_instance.dump_dict())

    async def delete(self, id_entity: int) -> None:
        model_instance = await self.session.get(self.model_class, id_entity)
        if model_instance:
            await self.session.delete(model_instance)
            logger.debug("Instance deleted")
        logger.debug("Instance %s not found", self.model_class)
