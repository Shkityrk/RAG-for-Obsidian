from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete

from src.database.models import ChatModel
from src.repositories.chat.interface import ChatRepository


class ChatSQLAlchemyRepository(ChatRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int, vault_id: Optional[int], title: str) -> dict:
        chat = ChatModel(
            user_id=user_id,
            vault_id=vault_id,
            title=title
        )
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return {
            "id": chat.id,
            "user_id": chat.user_id,
            "vault_id": chat.vault_id,
            "title": chat.title,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at
        }

    async def get_by_user(self, user_id: int) -> list[dict]:
        statement = select(ChatModel).where(ChatModel.user_id == user_id).order_by(ChatModel.updated_at.desc())
        result = await self.session.execute(statement)
        chats = result.scalars().all()
        return [
            {
                "id": chat.id,
                "user_id": chat.user_id,
                "vault_id": chat.vault_id,
                "title": chat.title,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at
            }
            for chat in chats
        ]

    async def get_by_id(self, chat_id: int) -> dict | None:
        statement = select(ChatModel).where(ChatModel.id == chat_id)
        result = await self.session.execute(statement)
        chat = result.scalar_one_or_none()
        if chat:
            return {
                "id": chat.id,
                "user_id": chat.user_id,
                "vault_id": chat.vault_id,
                "title": chat.title,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at
            }
        return None

    async def update_title(self, chat_id: int, title: str) -> None:
        statement = (
            select(ChatModel)
            .where(ChatModel.id == chat_id)
        )
        result = await self.session.execute(statement)
        chat = result.scalar_one_or_none()
        if chat:
            chat.title = title
            chat.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(chat)

    async def update_updated_at(self, chat_id: int) -> None:
        """Обновляет время последнего изменения чата"""
        statement = (
            select(ChatModel)
            .where(ChatModel.id == chat_id)
        )
        result = await self.session.execute(statement)
        chat = result.scalar_one_or_none()
        if chat:
            chat.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(chat)

    async def delete(self, chat_id: int) -> None:
        statement = delete(ChatModel).where(ChatModel.id == chat_id)
        await self.session.execute(statement)
        await self.session.commit()

