from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class FragmentInfo:
    """Информация о фрагменте текста из документа"""
    filename: str
    text: str
    similarity: float
    chunk_id: Optional[int] = None


@dataclass
class RagResponse:
    answer: str
    related_documents: list[str]
    used_tokens: tuple[int, int]
    fragments: list[FragmentInfo]  # Фрагменты, использованные для генерации ответа


class BaseRagService(ABC):

    @abstractmethod
    async def run(self, user_query: str) -> RagResponse:
        raise NotImplementedError
