from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.auth.dependencies import get_current_user
from src.api.chats.dependencies import get_chat_repository
from src.api.chats.schemas import CreateChatRequest, UpdateChatRequest, ChatListResponse, ChatResponse
from src.api.general_schemas import MessageResponse
from src.repositories.chat.interface import ChatRepository

chats_router = APIRouter(prefix="/chats", tags=["chats"])


@chats_router.post("/", response_model=ChatResponse)
async def create_chat(
    request: CreateChatRequest,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None
) -> ChatResponse:
    """Создать новый чат"""
    title = request.title or "New Chat"
    chat = await chat_repo.create(
        user_id=current_user["id"],
        vault_id=request.vault_id,
        title=title
    )
    return ChatResponse(**chat)


@chats_router.get("/", response_model=ChatListResponse)
async def list_chats(
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None
) -> ChatListResponse:
    """Получить список чатов пользователя"""
    chats = await chat_repo.get_by_user(current_user["id"])
    return ChatListResponse(
        chats=[ChatResponse(**chat) for chat in chats]
    )


@chats_router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None
) -> ChatResponse:
    """Получить информацию о чате"""
    chat = await chat_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    if chat["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    return ChatResponse(**chat)


@chats_router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    request: UpdateChatRequest,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None
) -> ChatResponse:
    """Обновить название чата"""
    chat = await chat_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    if chat["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    await chat_repo.update_title(chat_id, request.title)
    updated_chat = await chat_repo.get_by_id(chat_id)
    return ChatResponse(**updated_chat)


@chats_router.delete("/{chat_id}", response_model=MessageResponse)
async def delete_chat(
    chat_id: int,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None
) -> MessageResponse:
    """Удалить чат"""
    chat = await chat_repo.get_by_id(chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    if chat["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    await chat_repo.delete(chat_id)
    return MessageResponse(message="Chat deleted successfully")

