from abc import ABC, abstractmethod
from typing import Optional


class LLMTokensRepository(ABC):
    @abstractmethod
    async def create(self, user_id: int) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def add_tokens(self, user_id: int, input_tokens: int, output_tokens: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, user_id: int) -> Optional[dict]:
        raise NotImplementedError

    @abstractmethod
    async def clean(self, user_id: int) -> None:
        raise NotImplementedError
