from abc import ABC, abstractmethod


class UserRepository(ABC):
    @abstractmethod
    async def create(self, email: str, username: str, password_hash: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: int) -> dict | None:
        raise NotImplementedError

