from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CreateChatRequest(BaseModel):
    vault_id: Optional[int] = None
    title: Optional[str] = None


class UpdateChatRequest(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: int
    user_id: int
    vault_id: Optional[int]
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]

