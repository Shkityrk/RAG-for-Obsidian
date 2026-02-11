from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import app_config
from src.database.session import get_async_session
from src.repositories.llm_tokens.interface import LLMTokensRepository
from src.repositories.llm_tokens.sqlalchemy import LLMTokensSQLAlchemyRepository
from src.services.embeddings_service.base import BaseEmbeddingsService
from src.services.embeddings_service.ollama import OllamaEmbeddingsService
from src.services.llm_service.base import BaseLLMService
from src.services.llm_service.builder import LLMServiceBuilder
from src.services.rag_service.base import BaseRagService
from src.services.rag_service.dummy import DummyRagService
from src.services.rag_service.final import FinalRagService
from src.services.vector_store_service.base import BaseVectorStoreService
from src.services.vector_store_service.pgvector import PGVectorStoreService


def get_llm_tokens_repository(
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
) -> LLMTokensRepository:
    return LLMTokensSQLAlchemyRepository(db_session)


async def get_llm_service() -> BaseLLMService:
    """Get LLM service with hardcoded Ollama configuration."""
    return LLMServiceBuilder.build(
        vendor="Ollama",
        model=app_config.LLM_MODEL,
        token="",  # Not used for Ollama
        base_url=app_config.OLLAMA_BASE_URL,
        max_tokens=app_config.LLM_MAX_TOKENS,
    )


async def get_embeddings_service() -> BaseEmbeddingsService:
    """Get embeddings service with hardcoded Ollama configuration."""
    return OllamaEmbeddingsService(
        model=app_config.EMBEDDING_MODEL,
        base_url=app_config.OLLAMA_BASE_URL,
    )


def get_vector_store_service(
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
    embeddings_service: Annotated[BaseEmbeddingsService, Depends(get_embeddings_service)],
) -> BaseVectorStoreService:
    return PGVectorStoreService(db_session, embeddings_service)


def get_rag_service(
    llm_service: Annotated[BaseLLMService, Depends(get_llm_service)],
    vector_store_service: Annotated[BaseVectorStoreService, Depends(get_vector_store_service)],
) -> BaseRagService:
    # Always use FinalRagService - real RAG implementation
    return FinalRagService(llm_service, vector_store_service)
