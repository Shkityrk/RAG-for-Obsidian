import json
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import NonNegativeInt, PositiveInt

from src.api.auth.dependencies import get_current_user
from src.api.general_dependencies import get_llm_tokens_repository, get_rag_service
from src.api.general_schemas import MessageResponse
from src.api.messages.dependencies import get_message_repository
from src.api.messages.schemas import AnswerResponse, FragmentInfoSchema, MessageHistoryResponse, MessageSchema, QueryRequest
from src.api.chats.dependencies import get_chat_repository
from src.api.vaults.dependencies import get_vault_repository
from src.repositories.chat.interface import ChatRepository
from src.repositories.llm_tokens.interface import LLMTokensRepository
from src.repositories.message.interface import MessageRepository
from src.repositories.vault.interface import VaultRepository
from src.services.rag_service.base import BaseRagService

messages_router = APIRouter(prefix="/messages", tags=["messages"])


@messages_router.get("/", response_model=MessageHistoryResponse)
async def get_chat_messages(
    chat_id: Annotated[int, Query(description="ID чата")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None,
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)] = None,
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query(le=100)] = 100,
) -> MessageHistoryResponse:
    """Получить историю сообщений чата"""
    # Проверка прав доступа к чату
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
    
    message_dicts = await message_repo.get_many(chat_id, limit, offset)
    # Преобразуем fragments из словарей в FragmentInfoSchema
    messages = []
    for message_dict in message_dicts:
        fragments = message_dict.get("fragments", [])
        if fragments:
            message_dict["fragments"] = [
                FragmentInfoSchema(**fragment) if isinstance(fragment, dict) else fragment
                for fragment in fragments
            ]
        else:
            message_dict["fragments"] = []
        messages.append(MessageSchema(**message_dict))
    return MessageHistoryResponse(messages=messages)


@messages_router.post("/", response_model=AnswerResponse)
async def post_user_message(
    user_message: QueryRequest,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)] = None,
    llm_tokens_repository: Annotated[LLMTokensRepository, Depends(get_llm_tokens_repository)] = None,
    rag_service: Annotated[BaseRagService, Depends(get_rag_service)] = None,
) -> AnswerResponse:
    """Отправить сообщение в чат"""
    # Проверка прав доступа к чату
    chat = await chat_repo.get_by_id(user_message.chat_id)
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
    
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(user_message.vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to vault"
        )
    
    # Сохраняем вопрос пользователя
    await message_repo.create(chat_id=user_message.chat_id, content=user_message.content, role="user")
    
    # Генерируем ответ через RAG
    result = await rag_service.run(user_message.content, vault_id=user_message.vault_id)
    
    # Сохраняем ответ ассистента и получаем его ID
    # Преобразуем fragments в список словарей для сохранения
    fragments_dicts = [
        {
            "filename": fragment.filename,
            "text": fragment.text,
            "similarity": fragment.similarity,
            "chunk_id": fragment.chunk_id
        }
        for fragment in result.fragments
    ] if result.fragments else []
    
    assistant_message = await message_repo.create(
        chat_id=user_message.chat_id, 
        content=result.answer, 
        role="assistant",
        fragments=fragments_dicts if fragments_dicts else None
    )
    assistant_message_id = assistant_message["id"]
    
    # Обновляем токены пользователя
    await llm_tokens_repository.add_tokens(
        current_user["id"],
        result.used_tokens[0],
        result.used_tokens[1]
    )
    
    # Обновляем время последнего изменения чата
    await chat_repo.update_updated_at(user_message.chat_id)
    
    # Логируем fragments для отладки
    logger = logging.getLogger(__name__)
    logger.info(f"=== Creating AnswerResponse ===")
    logger.info(f"RAG result type: {type(result)}")
    logger.info(f"RAG result fragments count: {len(result.fragments) if result.fragments else 0}")
    logger.info(f"RAG result fragments: {result.fragments}")
    
    if result.fragments and len(result.fragments) > 0:
        logger.info(f"First fragment: filename={result.fragments[0].filename}, similarity={result.fragments[0].similarity}, chunk_id={result.fragments[0].chunk_id}")
    
    fragments_schemas = [
        FragmentInfoSchema(
            filename=fragment.filename,
            text=fragment.text,
            similarity=fragment.similarity,
            chunk_id=fragment.chunk_id
        )
        for fragment in (result.fragments or [])
    ]
    
    logger.info(f"Created {len(fragments_schemas)} fragment schemas")
    if fragments_schemas:
        logger.info(f"First schema: filename={fragments_schemas[0].filename}, similarity={fragments_schemas[0].similarity}")
    
    response = AnswerResponse(
        answer=result.answer,
        related_documents=result.related_documents,
        fragments=fragments_schemas,
        message_id=assistant_message_id
    )
    
    logger.info(f"AnswerResponse created with {len(response.fragments)} fragments")
    logger.info(f"AnswerResponse fragments: {response.fragments}")
    
    # Проверяем сериализацию
    try:
        response_dict = response.model_dump()
        logger.info(f"AnswerResponse model_dump() fragments count: {len(response_dict.get('fragments', []))}")
        logger.info(f"AnswerResponse model_dump() keys: {response_dict.keys()}")
        response_json = json.dumps(response_dict, ensure_ascii=False, default=str)
        logger.info(f"AnswerResponse JSON length: {len(response_json)}")
        logger.info(f"AnswerResponse JSON preview (first 500 chars): {response_json[:500]}")
    except Exception as e:
        logger.error(f"Error serializing response: {e}")
    
    return response


@messages_router.post("/combined", response_model=AnswerResponse)
async def post_combined_search_message(
    user_message: QueryRequest,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)] = None,
    llm_tokens_repository: Annotated[LLMTokensRepository, Depends(get_llm_tokens_repository)] = None,
    rag_service: Annotated[BaseRagService, Depends(get_rag_service)] = None,
) -> AnswerResponse:
    """Отправить сообщение с комбинированным поиском (Obsidian + Yandex)"""
    # Проверка прав доступа к чату
    chat = await chat_repo.get_by_id(user_message.chat_id)
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
    
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(user_message.vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to vault"
        )
    
    # Сохраняем вопрос пользователя
    await message_repo.create(chat_id=user_message.chat_id, content=user_message.content, role="user")
    
    # Проверяем, поддерживает ли RAG сервис комбинированный поиск
    if not hasattr(rag_service, 'run_combined_search'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Combined search is not supported by the current RAG service"
        )
    
    # Генерируем ответ через комбинированный поиск
    result = await rag_service.run_combined_search(user_message.content, vault_id=user_message.vault_id)
    
    # Сохраняем ответ ассистента и получаем его ID
    fragments_dicts = [
        {
            "filename": fragment.filename,
            "text": fragment.text,
            "similarity": fragment.similarity,
            "chunk_id": fragment.chunk_id
        }
        for fragment in result.fragments
    ] if result.fragments else []
    
    assistant_message = await message_repo.create(
        chat_id=user_message.chat_id, 
        content=result.answer, 
        role="assistant",
        fragments=fragments_dicts if fragments_dicts else None
    )
    assistant_message_id = assistant_message["id"]
    
    # Обновляем токены пользователя
    await llm_tokens_repository.add_tokens(
        current_user["id"],
        result.used_tokens[0],
        result.used_tokens[1]
    )
    
    # Обновляем время последнего изменения чата
    await chat_repo.update_updated_at(user_message.chat_id)
    
    fragments_schemas = [
        FragmentInfoSchema(
            filename=fragment.filename,
            text=fragment.text,
            similarity=fragment.similarity,
            chunk_id=fragment.chunk_id
        )
        for fragment in (result.fragments or [])
    ]
    
    return AnswerResponse(
        answer=result.answer,
        related_documents=result.related_documents,
        fragments=fragments_schemas,
        message_id=assistant_message_id
    )


@messages_router.delete("/", response_model=MessageResponse)
async def clean_message_history(
    chat_id: Annotated[int, Query(description="ID чата")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repository)] = None,
    message_repo: Annotated[MessageRepository, Depends(get_message_repository)] = None,
    llm_tokens_repository: Annotated[LLMTokensRepository, Depends(get_llm_tokens_repository)] = None,
) -> MessageResponse:
    """Очистить историю сообщений чата"""
    # Проверка прав доступа к чату
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
    
    await message_repo.clean_all(chat_id)
    await llm_tokens_repository.clean(current_user["id"])
    return MessageResponse(
        message="Chat messages have been successfully deleted"
    )
