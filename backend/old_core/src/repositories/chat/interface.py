from abc import ABC, abstractmethod
from typing import Optional


class ChatRepository(ABC):
    @abstractmethod
    async def create(self, user_id: int, vault_id: Optional[int], title: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user(self, user_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, chat_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    async def update_title(self, chat_id: int, title: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_updated_at(self, chat_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, chat_id: int) -> None:
        raise NotImplementedError

