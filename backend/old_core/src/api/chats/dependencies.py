from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.repositories.chat.interface import ChatRepository
from src.repositories.chat.sqlalchemy import ChatSQLAlchemyRepository


def get_chat_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> ChatRepository:
    """Получить репозиторий чатов"""
    return ChatSQLAlchemyRepository(session)

