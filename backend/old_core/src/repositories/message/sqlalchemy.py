import json
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from src.database.models import MessageModel
from src.repositories.message.interface import MessageRepository


class MessageSQLAlchemyRepository(MessageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, chat_id: int, content: str, role: str, fragments: Optional[list[dict]] = None) -> dict:
        fragments_json = json.dumps(fragments, ensure_ascii=False) if fragments else None
        message = MessageModel(chat_id=chat_id, content=content, role=role, fragments=fragments_json)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        result = message.model_dump()
        # Парсим fragments обратно в список для удобства
        if result.get("fragments"):
            result["fragments"] = json.loads(result["fragments"])
        else:
            result["fragments"] = []
        return result

    async def get_many(self, chat_id: int, limit: int, offset: int = 0) -> list[dict]:
        statement = (
            select(MessageModel)
            .where(MessageModel.chat_id == chat_id)
            .order_by(MessageModel.created_date.asc())  # Хронологический порядок для чата
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        messages = []
        for msg in result.scalars().all():
            msg_dict = msg.model_dump()
            # Парсим fragments из JSON
            if msg_dict.get("fragments"):
                try:
                    msg_dict["fragments"] = json.loads(msg_dict["fragments"])
                except (json.JSONDecodeError, TypeError):
                    msg_dict["fragments"] = []
            else:
                msg_dict["fragments"] = []
            messages.append(msg_dict)
        return messages

    async def clean_all(self, chat_id: int) -> None:
        statement = delete(MessageModel).where(MessageModel.chat_id == chat_id)
        await self.session.execute(statement)
        await self.session.commit()
