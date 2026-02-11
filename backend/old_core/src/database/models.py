import json
from datetime import datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class UserModel(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(..., unique=True, nullable=False, index=True)
    username: str = Field(..., unique=True, nullable=False, index=True)
    password_hash: str = Field(..., nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class VaultModel(SQLModel, table=True):
    __tablename__ = "vaults"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(..., foreign_key="users.id", nullable=False, index=True)
    name: str = Field(..., nullable=False)
    path: str = Field(..., nullable=False, unique=True)
    status: str = Field(default="ready", nullable=False)  # uploading, indexing, ready, error
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatModel(SQLModel, table=True):
    __tablename__ = "chats"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(..., foreign_key="users.id", nullable=False, index=True)
    vault_id: Optional[int] = Field(default=None, foreign_key="vaults.id", nullable=True)
    title: str = Field(..., nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MessageModel(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(..., foreign_key="chats.id", nullable=False, index=True)
    content: str = Field(..., nullable=False)
    role: str = Field(..., nullable=False)
    created_date: datetime = Field(default_factory=datetime.utcnow)
    fragments: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True), description="JSON массив fragments в формате JSON")


class LLMSettingsModel(SQLModel, table=True):
    __tablename__ = "llm_settings"

    id: int = Field(default=None, primary_key=True)
    vendor: str = Field(..., nullable=False)
    model: str = Field(..., nullable=False)
    base_url: str = Field(..., nullable=False)
    token: str = Field(..., nullable=False)
    max_tokens: int = Field(..., nullable=False)


class FileModel(SQLModel, table=True):
    __tablename__ = "files"

    id: int = Field(default=None, primary_key=True)
    vault_id: int = Field(..., foreign_key="vaults.id", nullable=False, index=True)
    name: str = Field(..., nullable=False)
    size: int = Field(..., nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    x: float = Field(..., nullable=False)
    y: float = Field(..., nullable=False)


class UpdateProcessModel(SQLModel, table=True):
    __tablename__ = "update_process"

    id: Optional[int] = Field(default=None, primary_key=True)
    vault_id: int = Field(..., foreign_key="vaults.id", nullable=False, index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)
    is_actual: bool = Field(default=True)


class ProgressStageModel(SQLModel, table=True):
    __tablename__ = "progress_stage"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(..., nullable=False)
    process_id: int = Field(..., nullable=False)
    progress: int = Field(..., nullable=False)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = Field(default=None)


class LLMTokensModel(SQLModel, table=True):
    __tablename__ = "llm_tokens"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(..., foreign_key="users.id", nullable=False, index=True)
    input_tokens: int = Field(default=0, nullable=False)
    output_tokens: int = Field(default=0, nullable=False)


class ChunkEmbeddingModel(SQLModel, table=True):
    __tablename__ = "chunk_embeddings"

    id: int = Field(default=None, primary_key=True)
    vault_id: int = Field(..., foreign_key="vaults.id", nullable=False, index=True)
    filename: str = Field(..., nullable=False)
    text: str = Field(..., nullable=False)
    embedding: Any = Field(sa_column=Column(Vector(1024)))
