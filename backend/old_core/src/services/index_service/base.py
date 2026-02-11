from abc import ABC, abstractmethod


class BaseIndexService(ABC):

    @abstractmethod
    async def find_files_to_update(self, vault_id: int) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def get_info(self, vault_id: int) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def get_clusters(self, vault_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    async def remove(self, vault_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update(self, vault_id: int, files: list[dict]) -> None:
        raise NotImplementedError
