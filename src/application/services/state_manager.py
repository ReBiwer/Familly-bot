from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

type URL = str


class IStateManager(ABC):
    @abstractmethod
    async def state_convert(self, state: str, payload: str, request: Mapping[str, Any]) -> URL:
        """Метод для конвертации состояния"""
        ...
