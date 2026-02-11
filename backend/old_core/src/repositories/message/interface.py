from abc import ABC, abstractmethod
from typing import Literal, Optional


class MessageRepository(ABC):
    @abstractmethod
    async def create(self, chat_id: int, content: str, role: Literal["user", "assistant"], fragments: Optional[list[dict]] = None) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def get_many(self, chat_id: int, limit: int, offset: int = 0) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def clean_all(self, chat_id: int) -> None:
        raise NotImplementedError
