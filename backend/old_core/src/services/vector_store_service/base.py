from abc import ABC, abstractmethod


class BaseVectorStoreService(ABC):

    @abstractmethod
    async def retrieve(self, query: str, k: int, vault_id: int, similarity_threshold: float | None = None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def add_chunks(self, vault_id: int, texts: list[str], filenames: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_chunks_of_file(self, vault_id: int, filename: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def remove_all_chunks(self, vault_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_chunks_of_file(self, vault_id: int, filename: str) -> list[dict]:
        raise NotImplementedError
