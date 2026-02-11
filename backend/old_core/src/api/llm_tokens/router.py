from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.auth.dependencies import get_current_user
from src.api.general_dependencies import get_llm_tokens_repository
from src.api.llm_tokens.schemas import LLMTokensResponse
from src.repositories.llm_tokens.interface import LLMTokensRepository

llm_tokens_router = APIRouter(prefix="/llm_tokens", tags=["llm tokens"])


@llm_tokens_router.get("/", response_model=LLMTokensResponse)
async def get_llm_tokens(
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    llm_tokens_repo: Annotated[LLMTokensRepository, Depends(get_llm_tokens_repository)] = None,
) -> LLMTokensResponse:
    """Получить статистику использованных токенов пользователя"""
    llm_tokens_dict = await llm_tokens_repo.get(current_user["id"])
    if not llm_tokens_dict:
        llm_tokens_dict = await llm_tokens_repo.create(current_user["id"])
    return LLMTokensResponse(**llm_tokens_dict)
