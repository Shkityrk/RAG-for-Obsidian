from abc import ABC, abstractmethod
from typing import Optional


class VaultRepository(ABC):
    @abstractmethod
    async def create(self, user_id: int, name: str, path: str, status: str = "ready") -> dict:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user(self, user_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, vault_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    async def update_status(self, vault_id: int, status: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_path(self, vault_id: int, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, vault_id: int) -> None:
        raise NotImplementedError

