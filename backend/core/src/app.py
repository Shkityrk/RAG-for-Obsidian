import hashlib
import json
import logging
import os
import re
import threading
import time
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Query
from jose import JWTError, jwt
from minio import Minio
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from sqlalchemy import DateTime, Integer, String, Text, create_engine, or_, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.sql import quoted_name


logger = logging.getLogger("core")
logging.basicConfig(level=os.getenv("CORE_LOG_LEVEL", "INFO"))


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_NAME = os.getenv("POSTGRES_NAME", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_NAME}"
)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true"}

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "vault_embeddings")

EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "openrouter").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_EMBED_MODEL = os.getenv("OPENROUTER_EMBED_MODEL", "baai/bge-m3")
OPENROUTER_LLM_MODEL = os.getenv("OPENROUTER_LLM_MODEL", "google/gemini-3-flash-preview")
OPENROUTER_DEEP_RESEARCH_MODEL = os.getenv(
    "OPENROUTER_DEEP_RESEARCH_MODEL",
    "perplexity/sonar-deep-research",
)
_EMBEDDING_DIM_RAW = os.getenv("EMBEDDING_DIM")
if _EMBEDDING_DIM_RAW is not None:
    EMBEDDING_DIM = int(_EMBEDDING_DIM_RAW)
elif EMBEDDINGS_PROVIDER == "openrouter":
    # baai/bge-m3 и многие модели на OpenRouter — 1024 измерения
    EMBEDDING_DIM = 1024
else:
    EMBEDDING_DIM = 768
EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "32"))

POLL_INTERVAL_SECONDS = int(os.getenv("CORE_POLL_INTERVAL_SECONDS", str(5 * 60)))
DELAY_AFTER_NEW_FILE_SECONDS = int(os.getenv("CORE_DELAY_AFTER_NEW_FILE_SECONDS", "60"))
MAX_NEW_FILE_WORKERS = int(os.getenv("CORE_MAX_NEW_FILE_WORKERS", "5"))
DB_BATCH_SIZE = int(os.getenv("CORE_DB_BATCH_SIZE", "50"))
RETRY_AFTER_MINUTES = int(os.getenv("CORE_RETRY_AFTER_MINUTES", "5"))
MAX_SOURCE_TEXT_BYTES = int(os.getenv("CORE_MAX_SOURCE_TEXT_BYTES", str(8 * 1024 * 1024)))
QDRANT_UPSERT_BATCH_SIZE = int(os.getenv("CORE_QDRANT_UPSERT_BATCH_SIZE", "128"))
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret")
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
RAG_AGENT_TOP_K = int(os.getenv("RAG_AGENT_TOP_K", "5"))
RAG_AGENT_SEARCH_LIMIT = int(os.getenv("RAG_AGENT_SEARCH_LIMIT", "40"))
RAG_AGENT_MAX_SUBQUERIES = int(os.getenv("RAG_AGENT_MAX_SUBQUERIES", "4"))
RAG_AGENT_HISTORY_MESSAGES = int(os.getenv("RAG_AGENT_HISTORY_MESSAGES", "8"))
RAG_AGENT_CONTEXT_FRAGMENT_CHARS = int(os.getenv("RAG_AGENT_CONTEXT_FRAGMENT_CHARS", "1000"))
CHAT_TITLE_MAX_CHARS = int(os.getenv("CHAT_TITLE_MAX_CHARS", "48"))
INT32_MAX = 2_147_483_647

DEFAULT_LLM_SETTINGS: dict[str, Any] = {
    "openrouter_api_key": OPENROUTER_API_KEY,
    "openrouter_llm_model": OPENROUTER_LLM_MODEL,
    "openrouter_deep_research_model": OPENROUTER_DEEP_RESEARCH_MODEL,
    "temperature": 0.2,
    "top_p": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "max_tokens": 900,
    "deep_research_temperature": 0.1,
    "deep_research_top_p": 1.0,
    "deep_research_presence_penalty": 0.0,
    "deep_research_frequency_penalty": 0.0,
    "deep_research_max_tokens": 1600,
}


class Base(DeclarativeBase):
    pass


class VaultIndex(Base):
    __tablename__ = quoted_name("index", True)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[str] = mapped_column(String, nullable=False, index=True)
    minio_object_name: Mapped[str | None] = mapped_column(String, nullable=True)
    minio_bucket_name: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    processing_status: Mapped[str] = mapped_column(String, nullable=False)
    status_index: Mapped[str] = mapped_column(String, nullable=False, default="READY")
    index_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    vault_path: Mapped[str] = mapped_column(String, nullable=False)
    old_vault_path: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatModel(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    vault_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    created_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fragments: Mapped[str | None] = mapped_column(Text, nullable=True)


class NewFilePayload(BaseModel):
    username: str
    vault_path: str
    status_index: str
    minio_bucket_name: str
    minio_object_name: str


class VaultStats(BaseModel):
    collection: str
    total_points: int
    unique_files: int
    unique_users: int
    chunks_by_user: dict[str, int]
    generated_at: str


class MessageResponse(BaseModel):
    message: str


class IndexInfoResponse(BaseModel):
    n_documents_to_update: int
    n_all_documents: int
    last_update_time: str | None
    in_update_process: bool


class ClusterSchema(BaseModel):
    name: str
    x: float
    y: float


class ClustersResponse(BaseModel):
    clusters: list[ClusterSchema]


class StageProgressSchema(BaseModel):
    name: str
    value: int


class UpdateIndexProgressResponse(BaseModel):
    in_progress: bool
    stages: list[StageProgressSchema]


class VaultSchema(BaseModel):
    id: int
    user_id: int
    name: str
    path: str
    status: str
    created_at: str
    updated_at: str


class VaultListResponse(BaseModel):
    vaults: list[VaultSchema]


class VaultFileResponse(BaseModel):
    filename: str
    content: str
    path: str


# Chat schemas
class CreateChatRequest(BaseModel):
    vault_id: int | None = None
    title: str | None = None


class UpdateChatRequest(BaseModel):
    title: str


class ChatResponse(BaseModel):
    id: int
    user_id: int
    vault_id: int | None
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]


# Message schemas
class FragmentInfoSchema(BaseModel):
    filename: str
    text: str
    similarity: float
    chunk_id: int | None = None


class MessageSchema(BaseModel):
    id: int
    role: str
    content: str
    created_date: datetime
    fragments: list[FragmentInfoSchema] = []


class MessageHistoryResponse(BaseModel):
    messages: list[MessageSchema]


class QueryRequest(BaseModel):
    content: str
    chat_id: int
    vault_id: int


class AnswerResponse(BaseModel):
    answer: str
    related_documents: list[str]
    fragments: list[FragmentInfoSchema] = []
    message_id: int


class LLMTokensResponse(BaseModel):
    input_tokens: int
    output_tokens: int


class LLMAvailabilityResponse(BaseModel):
    is_available: bool
    error_message: str


class LLMSettingsRequest(BaseModel):
    openrouter_api_key: str
    openrouter_llm_model: str
    openrouter_deep_research_model: str
    temperature: float = 0.2
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    max_tokens: int = 900
    deep_research_temperature: float = 0.1
    deep_research_top_p: float = 1.0
    deep_research_presence_penalty: float = 0.0
    deep_research_frequency_penalty: float = 0.0
    deep_research_max_tokens: int = 1600


class LLMSettingsResponse(LLMSettingsRequest):
    pass


class EmbeddingsService:
    def __init__(self, batch_size: int = EMBED_BATCH_SIZE) -> None:
        self.batch_size = batch_size

    def embed_many(
        self,
        texts: list[str],
        *,
        openrouter_api_key: str | None = None,
        openrouter_model: str | None = None,
        provider: str | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            vectors.extend(
                self._embed_batch(
                    batch,
                    openrouter_api_key=openrouter_api_key,
                    openrouter_model=openrouter_model,
                    provider=provider,
                )
            )
        return vectors

    def _embed_batch(
        self,
        batch: list[str],
        *,
        openrouter_api_key: str | None = None,
        openrouter_model: str | None = None,
        provider: str | None = None,
    ) -> list[list[float]]:
        effective_provider = (provider or EMBEDDINGS_PROVIDER).lower()
        effective_api_key = openrouter_api_key or OPENROUTER_API_KEY
        effective_model = openrouter_model or OPENROUTER_EMBED_MODEL

        if effective_provider == "openrouter":
            if not effective_api_key:
                logger.warning("OpenRouter API key is empty, fallback to hash embeddings")
                return [self._embed_hash(text) for text in batch]
            try:
                return self._embed_openrouter(
                    batch,
                    api_key=effective_api_key,
                    model=effective_model,
                )
            except Exception as exc:
                logger.warning("OpenRouter embedding failed, fallback to hash embeddings: %s", exc)
                return [self._embed_hash(text) for text in batch]
        if effective_provider == "ollama":
            try:
                return [self._embed_ollama(text) for text in batch]
            except Exception as exc:
                logger.warning("Ollama embedding failed, fallback to hash embeddings: %s", exc)
        return [self._embed_hash(text) for text in batch]

    @staticmethod
    def _embed_ollama(text_value: str) -> list[float]:
        payload = {"model": OLLAMA_EMBED_MODEL, "input": text_value}
        with httpx.Client(timeout=60.0) as client:
            # New Ollama API uses /api/embed. /api/embeddings is legacy fallback.
            response = client.post(f"{OLLAMA_BASE_URL}/api/embed", json=payload)
            if response.status_code == 404:
                legacy_payload = {"model": OLLAMA_EMBED_MODEL, "prompt": text_value}
                response = client.post(f"{OLLAMA_BASE_URL}/api/embeddings", json=legacy_payload)
            response.raise_for_status()
            data = response.json()
        embedding = data.get("embedding")
        if embedding is None and isinstance(data.get("embeddings"), list) and data["embeddings"]:
            embedding = data["embeddings"][0]
        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError("Invalid Ollama embeddings response format")
        return [float(x) for x in embedding]

    @staticmethod
    def _embed_openrouter(batch: list[str], *, api_key: str, model: str) -> list[list[float]]:
        payload = {"model": model, "input": batch}
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{OPENROUTER_BASE_URL}/embeddings", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        rows = data.get("data")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError("Invalid OpenRouter embeddings response format")

        vectors: list[list[float]] = []
        for item in rows:
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError("Invalid OpenRouter embedding item format")
            vectors.append([float(x) for x in embedding])
        return vectors

    @staticmethod
    def _embed_hash(text_value: str) -> list[float]:
        # Deterministic fallback: keeps pipeline alive if embedding provider is down.
        result: list[float] = []
        digest_input = text_value.encode("utf-8", errors="ignore")
        counter = 0
        while len(result) < EMBEDDING_DIM:
            digest = hashlib.sha256(digest_input + counter.to_bytes(4, "little")).digest()
            for b in digest:
                result.append((b / 127.5) - 1.0)
                if len(result) == EMBEDDING_DIM:
                    break
            counter += 1
        return result


def split_text(content: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    normalized = content.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def _extract_username_from_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization bearer token is required")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    username = payload.get("sub")
    if not isinstance(username, str) or not username:
        raise HTTPException(status_code=401, detail="Token does not contain username")
    return username


def _extract_user_id_from_token(authorization: str | None) -> int:
    """Extract user_id from JWT token.

    Supports both legacy tokens (sub=user_id) and current auth tokens (sub=username).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization bearer token is required")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, AUTH_SECRET_KEY, algorithms=[AUTH_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=401, detail="Token does not contain subject")

    # Legacy behavior: subject already contains user_id.
    try:
        return int(subject)
    except (ValueError, TypeError):
        pass

    # Current behavior: subject contains username.
    username = str(subject).strip()
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    with indexer.session_local() as db:
        row = db.execute(text("SELECT id FROM users WHERE username = :username"), {"username": username}).first()
    if row is None:
        raise HTTPException(status_code=401, detail="User not found")
    return int(row[0])


def _vault_root_from_path(vault_path: str) -> str:
    # In this architecture file paths are relative to a single user vault.
    # Keep one logical vault for the whole user, regardless of file path.
    _ = vault_path
    return "default"


def _stable_vault_id(username: str, vault_root: str) -> int:
    digest = hashlib.sha1(f"{username}::{vault_root}".encode("utf-8")).hexdigest()
    # Keep vault_id in signed int32 range to match existing DB schema (INTEGER).
    return int(digest[:8], 16) & INT32_MAX


def _legacy_stable_vault_id(username: str, vault_root: str) -> int:
    digest = hashlib.sha1(f"{username}::{vault_root}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _legacy_vault_root_from_path(vault_path: str) -> str:
    normalized = vault_path.replace("\\", "/").strip("/")
    if not normalized:
        return "default"
    return normalized.split("/")[0]


def _vault_id_matches(username: str, vault_path: str, vault_id: int) -> bool:
    current_root = _vault_root_from_path(vault_path)
    legacy_root = _legacy_vault_root_from_path(vault_path)
    candidates = {
        _stable_vault_id(username, current_root),
        _legacy_stable_vault_id(username, current_root),
        _stable_vault_id(username, legacy_root),
        _legacy_stable_vault_id(username, legacy_root),
    }
    return vault_id in candidates


def _read_qdrant_vector_size(collection_info: Any) -> int | None:
    try:
        params = collection_info.config.params
        if params is None:
            return None
        vectors = params.vectors
        if vectors is None:
            return None
        if isinstance(vectors, dict):
            for v in vectors.values():
                if hasattr(v, "size"):
                    return int(v.size)
            return None
        if hasattr(vectors, "size"):
            return int(vectors.size)
    except Exception:
        return None
    return None


def _parse_json_object(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    return {}


def _derive_chat_title_from_message(message_content: str, max_chars: int = CHAT_TITLE_MAX_CHARS) -> str:
    normalized = " ".join(message_content.split()).strip()
    if not normalized:
        return "New Chat"
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()


class OpenRouterLLMService:
    def __init__(self) -> None:
        self.base_url = OPENROUTER_BASE_URL.rstrip("/")
        self.api_key = OPENROUTER_API_KEY
        self.model = OPENROUTER_LLM_MODEL

    @staticmethod
    def _extract_text(content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, dict):
            text_value = content.get("text")
            return str(text_value).strip() if text_value is not None else ""
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    text_value = item.get("text", "")
                    if text_value:
                        parts.append(str(text_value))
            return "\n".join(parts).strip()
        return ""

    def run(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 900,
        model: str | None = None,
        api_key: str | None = None,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
    ) -> tuple[str, tuple[int, int]]:
        effective_api_key = api_key or self.api_key
        if not effective_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        payload = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if top_p is not None:
            payload["top_p"] = top_p
        if presence_penalty is not None:
            payload["presence_penalty"] = presence_penalty
        if frequency_penalty is not None:
            payload["frequency_penalty"] = frequency_penalty
        headers = {
            "Authorization": f"Bearer {effective_api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=90.0) as client:
            response = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("Invalid OpenRouter response: choices are missing")

        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get("message", {}) if isinstance(first_choice, dict) else {}
        answer_text = self._extract_text(message.get("content", ""))
        if not answer_text:
            raise RuntimeError("OpenRouter returned an empty completion")

        usage = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        return answer_text, (prompt_tokens, completion_tokens)


class VaultChatAgent:
    def __init__(self, embeddings: EmbeddingsService, qdrant_client: QdrantClient, llm: OpenRouterLLMService) -> None:
        self.embeddings = embeddings
        self.qdrant_client = qdrant_client
        self.llm = llm

    @staticmethod
    def _normalize_query(text_value: str) -> str:
        return " ".join(text_value.strip().split())

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _belongs_to_vault(username: str, vault_id: int, payload: dict[str, Any]) -> bool:
        payload_vault_id = payload.get("vault_id")
        payload_vault_id_int = VaultChatAgent._safe_int(payload_vault_id)
        if payload_vault_id_int is not None:
            if payload_vault_id_int == vault_id:
                return True

        vault_path = str(payload.get("vault_path", ""))
        if not vault_path:
            return False
        return _vault_id_matches(username=username, vault_path=vault_path, vault_id=vault_id)

    def _decompose_query(
        self,
        user_query: str,
        *,
        llm_model: str | None = None,
        api_key: str | None = None,
    ) -> tuple[list[str], tuple[int, int]]:
        normalized_query = self._normalize_query(user_query)
        if not normalized_query:
            return [], (0, 0)

        system_prompt = (
            "Ты разбиваешь запрос пользователя на подзапросы для семантического поиска по Obsidian-заметкам. "
            "Верни только JSON-объект формата {\"search_queries\": [\"...\", \"...\"]}. "
            "Подзапросы должны быть короткими и конкретными."
        )
        user_prompt = (
            f"Исходный запрос: {normalized_query}\n"
            f"Ограничения: максимум {RAG_AGENT_MAX_SUBQUERIES} подзапроса, только русский или английский текст, "
            "без комментариев и markdown."
        )

        try:
            llm_text, usage = self.llm.run(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=220,
                model=llm_model,
                api_key=api_key,
            )
            payload = _parse_json_object(llm_text)
            raw_queries = payload.get("search_queries", [])
            prepared: list[str] = [normalized_query]
            if isinstance(raw_queries, list):
                for item in raw_queries:
                    normalized = self._normalize_query(str(item))
                    if not normalized:
                        continue
                    if len(normalized) > 300:
                        continue
                    if normalized.casefold() in {query.casefold() for query in prepared}:
                        continue
                    prepared.append(normalized)
                    if len(prepared) >= RAG_AGENT_MAX_SUBQUERIES:
                        break
            return prepared[:RAG_AGENT_MAX_SUBQUERIES], usage
        except Exception as exc:
            logger.warning("Failed to decompose user query with LLM, using original query only: %s", exc)
            return [normalized_query], (0, 0)

    def _retrieve_fragments(
        self,
        *,
        username: str,
        vault_id: int,
        search_queries: list[str],
        api_key: str | None,
    ) -> list[FragmentInfoSchema]:
        if not search_queries:
            return []

        vectors = self.embeddings.embed_many(
            search_queries,
            openrouter_api_key=api_key,
            openrouter_model=OPENROUTER_EMBED_MODEL,
            provider="openrouter",
        )
        if not vectors:
            return []

        aggregated: dict[str, tuple[float, FragmentInfoSchema]] = {}
        for vector in vectors:
            try:
                points = self._semantic_search_points(username=username, vector=vector)
            except Exception as exc:
                logger.warning("Qdrant semantic search failed: %s", exc)
                continue

            for point in points:
                payload = point.payload if isinstance(point.payload, dict) else {}
                if not payload:
                    continue
                if not self._belongs_to_vault(username, vault_id, payload):
                    continue

                fragment_text = str(payload.get("text", "")).strip()
                if not fragment_text:
                    continue
                if len(fragment_text) > RAG_AGENT_CONTEXT_FRAGMENT_CHARS:
                    fragment_text = fragment_text[:RAG_AGENT_CONTEXT_FRAGMENT_CHARS]

                score = float(getattr(point, "score", 0.0) or 0.0)
                vault_path = str(payload.get("vault_path", ""))
                filename = vault_path.replace("\\", "/").split("/")[-1] or "unknown.md"
                chunk_id = self._safe_int(payload.get("chunk_index"))
                doc_key = str(payload.get("doc_key") or f"{username}::{vault_path}")
                unique_key = f"{doc_key}::{chunk_id if chunk_id is not None else point.id}"

                fragment = FragmentInfoSchema(
                    filename=filename,
                    text=fragment_text,
                    similarity=score,
                    chunk_id=chunk_id,
                )
                previous = aggregated.get(unique_key)
                if previous is None or score > previous[0]:
                    aggregated[unique_key] = (score, fragment)

        ranked_fragments = [item[1] for item in sorted(aggregated.values(), key=lambda x: x[0], reverse=True)]
        return ranked_fragments[:RAG_AGENT_TOP_K]

    def _semantic_search_points(self, *, username: str, vector: list[float]) -> list[Any]:
        search_filter = Filter(
            must=[FieldCondition(key="username", match=MatchValue(value=username))]
        )

        # Old qdrant-client API.
        if hasattr(self.qdrant_client, "search"):
            return self.qdrant_client.search(
                collection_name=QDRANT_COLLECTION,
                query_vector=vector,
                query_filter=search_filter,
                limit=RAG_AGENT_SEARCH_LIMIT,
                with_payload=True,
            )

        # New qdrant-client API.
        if hasattr(self.qdrant_client, "query_points"):
            response = self.qdrant_client.query_points(
                collection_name=QDRANT_COLLECTION,
                query=vector,
                query_filter=search_filter,
                limit=RAG_AGENT_SEARCH_LIMIT,
                with_payload=True,
            )
            if isinstance(response, list):
                return response
            points = getattr(response, "points", None)
            if isinstance(points, list):
                return points
            result = getattr(response, "result", None)
            if isinstance(result, list):
                return result
            return []

        raise RuntimeError("Qdrant client does not support vector search API")

    @staticmethod
    def _render_history(chat_history: list[dict[str, str]]) -> str:
        if not chat_history:
            return "История отсутствует."
        lines: list[str] = []
        for message in chat_history:
            role = message.get("role", "user")
            content = " ".join(message.get("content", "").split())
            if not content:
                continue
            lines.append(f"{role}: {content}")
        return "\n".join(lines) if lines else "История отсутствует."

    @staticmethod
    def _render_context(fragments: list[FragmentInfoSchema]) -> str:
        if not fragments:
            return "Релевантный контекст в vault не найден."
        lines: list[str] = []
        for idx, fragment in enumerate(fragments, start=1):
            lines.append(
                f"[Фрагмент {idx}] Файл: {fragment.filename}; similarity={fragment.similarity:.4f}\n{fragment.text}"
            )
        return "\n\n".join(lines)

    @staticmethod
    def _fallback_answer(user_query: str, fragments: list[FragmentInfoSchema]) -> str:
        if not fragments:
            return (
                "Я не нашел релевантного контекста в вашем vault для этого вопроса. "
                "Уточните формулировку или убедитесь, что нужные заметки проиндексированы."
            )
        preview = "\n".join(
            f"- {fragment.filename}: {fragment.text[:180].strip()}"
            for fragment in fragments[:3]
        )
        return (
            "Не удалось получить ответ от LLM, поэтому возвращаю найденные фрагменты из vault:\n"
            f"{preview}\n\nВопрос: {user_query}"
        )

    @staticmethod
    def _looks_like_no_context_answer(answer: str) -> bool:
        lowered = answer.casefold()
        markers = [
            "не найдено",
            "не наш",
            "нет информации в vault",
            "не найдено замет",
            "в вашем obsidian vault не найдено",
        ]
        return any(marker in lowered for marker in markers)

    @staticmethod
    def _grounded_answer_from_fragments(user_query: str, fragments: list[FragmentInfoSchema]) -> str:
        top = fragments[:4]
        if not top:
            return "Не найден релевантный контекст в заметках."
        lines = [f"- {item.filename}: {item.text[:260].strip()}" for item in top]
        return (
            "По вашим заметкам найден релевантный контекст. "
            f"Краткая выжимка по запросу «{user_query}»:\n"
            + "\n".join(lines)
        )

    def run(
        self,
        *,
        username: str,
        vault_id: int,
        user_query: str,
        chat_history: list[dict[str, str]],
        settings: dict[str, Any],
        deep_research: bool = False,
    ) -> tuple[str, list[str], list[FragmentInfoSchema], tuple[int, int]]:
        api_key = str(settings.get("openrouter_api_key", "") or "").strip()
        response_model = str(
            settings.get("openrouter_deep_research_model" if deep_research else "openrouter_llm_model")
            or (OPENROUTER_DEEP_RESEARCH_MODEL if deep_research else OPENROUTER_LLM_MODEL)
        )
        search_queries, decompose_usage = self._decompose_query(
            user_query,
            llm_model=response_model,
            api_key=api_key,
        )
        fragments = self._retrieve_fragments(
            username=username,
            vault_id=vault_id,
            search_queries=search_queries,
            api_key=api_key,
        )
        related_documents = sorted({fragment.filename for fragment in fragments})

        if deep_research:
            system_prompt = (
                "Ты Deep Research агент по заметкам пользователя в Obsidian vault. "
                "Отвечай строго на поставленный вопрос, без лишних отступлений. "
                "Ответ должен быть кратким и по существу (обычно 2-5 предложений). "
                "Опирайся только на найденные фрагменты. "
                "Если данных в заметках недостаточно, прямо укажи, чего именно не хватает. "
                "Не заявляй, что заметок нет, если контекст передан."
            )
        elif fragments:
            system_prompt = (
                "Ты агент для ответов по Obsidian vault. "
                "Контекст уже найден, поэтому отвечай строго по этому контексту. "
                "Отвечай кратко и только по поставленному вопросу (обычно 1-4 предложения). "
                "Запрещено утверждать, что заметок не найдено."
            )
        else:
            system_prompt = (
                "Ты агент для ответов по Obsidian vault. "
                "Используй в первую очередь контекст из заметок. "
                "Отвечай кратко и только по поставленному вопросу (обычно 1-4 предложения). "
                "Если контекст нерелевантен или отсутствует, честно скажи об этом."
            )
        user_prompt = (
            f"История чата:\n{self._render_history(chat_history)}\n\n"
            f"Исходный вопрос пользователя:\n{user_query}\n\n"
            f"Сформированные подзапросы для поиска:\n{json.dumps(search_queries, ensure_ascii=False)}\n\n"
            f"Контекст из vault:\n{self._render_context(fragments)}\n\n"
            "Сформируй короткий ответ строго по вопросу пользователя. "
            "Без вводных фраз, без общих рассуждений, без ухода в сторону. "
            "Если в контексте нет фактов для ответа, напиши это одной короткой фразой."
        )

        try:
            answer, answer_usage = self._run_llm_with_retry(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=float(
                    settings.get("deep_research_temperature" if deep_research else "temperature", 0.1 if deep_research else 0.2)
                ),
                max_tokens=int(
                    settings.get("deep_research_max_tokens" if deep_research else "max_tokens", 1600 if deep_research else 900)
                ),
                attempts=4 if deep_research else 3,
                retry_delay_seconds=1.5,
                model=response_model,
                api_key=api_key,
                top_p=float(
                    settings.get("deep_research_top_p" if deep_research else "top_p", 1.0)
                ),
                presence_penalty=float(
                    settings.get(
                        "deep_research_presence_penalty" if deep_research else "presence_penalty",
                        0.0,
                    )
                ),
                frequency_penalty=float(
                    settings.get(
                        "deep_research_frequency_penalty" if deep_research else "frequency_penalty",
                        0.0,
                    )
                ),
            )
            total_usage = (
                decompose_usage[0] + answer_usage[0],
                decompose_usage[1] + answer_usage[1],
            )
            if fragments and self._looks_like_no_context_answer(answer):
                logger.warning(
                    "LLM returned no-context style answer despite retrieved fragments, forcing grounded fallback summary"
                )
                answer = self._grounded_answer_from_fragments(user_query, fragments)
            return answer, related_documents, fragments, total_usage
        except Exception as exc:
            logger.warning("Failed to generate final answer with OpenRouter LLM: %s", exc)
            fallback = self._fallback_answer(user_query, fragments)
            return fallback, related_documents, fragments, decompose_usage

    def _run_llm_with_retry(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        attempts: int,
        retry_delay_seconds: float,
        model: str | None = None,
        api_key: str | None = None,
        top_p: float | None = None,
        presence_penalty: float | None = None,
        frequency_penalty: float | None = None,
    ) -> tuple[str, tuple[int, int]]:
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self.llm.run(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model,
                    api_key=api_key,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                )
            except Exception as exc:
                last_error = exc
                if attempt == attempts:
                    break
                logger.warning(
                    "OpenRouter final-answer attempt %s/%s failed, retrying in %.1fs: %s",
                    attempt,
                    attempts,
                    retry_delay_seconds,
                    exc,
                )
                time.sleep(retry_delay_seconds)
        if last_error is None:
            raise RuntimeError("LLM generation failed without a captured error")
        raise last_error


class CoreIndexer:
    def __init__(self) -> None:
        self.engine = create_engine(DATABASE_URL)
        self.session_local = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        self.qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self.embeddings = EmbeddingsService()
        self._scan_lock = threading.Lock()
        self._poller_stop = threading.Event()
        self._poller_thread: threading.Thread | None = None
        self._new_file_executor = ThreadPoolExecutor(
            max_workers=MAX_NEW_FILE_WORKERS,
            thread_name_prefix="core-new-file",
        )
        self._progress_lock = threading.Lock()
        self._progress_by_key: dict[str, UpdateIndexProgressResponse] = {}

    def startup(self) -> None:
        Base.metadata.create_all(bind=self.engine)
        self._ensure_llm_tokens_table()
        self._ensure_user_llm_settings_table()
        self._ensure_qdrant_collection()
        self._start_poller()
        logger.info("Core indexer started: poll interval=%ss", POLL_INTERVAL_SECONDS)

    def shutdown(self) -> None:
        self._poller_stop.set()
        if self._poller_thread is not None:
            self._poller_thread.join(timeout=3)
        self._new_file_executor.shutdown(wait=False, cancel_futures=True)
        logger.info("Core indexer stopped")

    def schedule_delayed_scan(self) -> None:
        self._new_file_executor.submit(self._delayed_scan_task)

    def schedule_vault_reindex(self, username: str, vault_id: int) -> None:
        self._new_file_executor.submit(self._reindex_vault_task, username, vault_id)

    def _delayed_scan_task(self) -> None:
        time.sleep(DELAY_AFTER_NEW_FILE_SECONDS)
        self.run_indexing_pass(reason="new_file_delayed")

    def _reindex_vault_task(self, username: str, vault_id: int) -> None:
        progress_key = f"{username}:{vault_id}"
        self._set_progress(
            progress_key,
            UpdateIndexProgressResponse(
                in_progress=True,
                stages=[
                    StageProgressSchema(name="1. Vectorization", value=0),
                    StageProgressSchema(name="2. Updating index", value=0),
                ],
            ),
        )
        try:
            processed = self.reindex_vault(username=username, vault_id=vault_id, progress_key=progress_key)
            self._set_stage_value(progress_key, 0, 100)
            self._set_stage_value(progress_key, 1, 100)
            logger.info("Manual vault reindex complete, username=%s vault_id=%s rows=%s", username, vault_id, processed)
        except Exception:
            logger.exception("Manual vault reindex failed, username=%s vault_id=%s", username, vault_id)
        finally:
            self._set_progress(progress_key, UpdateIndexProgressResponse(in_progress=False, stages=[]))

    def _start_poller(self) -> None:
        if self._poller_thread and self._poller_thread.is_alive():
            return
        self._poller_thread = threading.Thread(target=self._poller_loop, daemon=True, name="core-poller")
        self._poller_thread.start()

    def _poller_loop(self) -> None:
        while not self._poller_stop.is_set():
            self.run_indexing_pass(reason="periodic")
            self._poller_stop.wait(POLL_INTERVAL_SECONDS)

    def run_indexing_pass(self, reason: str) -> None:
        if not self._scan_lock.acquire(blocking=False):
            logger.info("Skip scan (%s): another scan is already running", reason)
            return
        try:
            processed = 0
            for row in self._iter_due_rows():
                self._process_row(row)
                processed += 1
            if processed:
                logger.info("Index scan (%s) completed, processed rows=%s", reason, processed)
        except Exception:
            logger.exception("Index scan (%s) failed", reason)
        finally:
            self._scan_lock.release()

    def reindex_vault(self, username: str, vault_id: int, progress_key: str | None = None) -> int:
        if not self._scan_lock.acquire(blocking=False):
            logger.info("Skip vault reindex: another scan is already running")
            return 0
        try:
            rows = self._iter_rows_for_vault(username=username, vault_id=vault_id)
            total = len(rows)
            if total == 0:
                return 0
            processed = 0
            for row in rows:
                self._process_row(row)
                processed += 1
                if progress_key:
                    value = int(processed * 100 / total)
                    self._set_stage_value(progress_key, 0, value)
                    self._set_stage_value(progress_key, 1, value)
            return processed
        finally:
            self._scan_lock.release()

    def _iter_due_rows(self) -> Iterator[VaultIndex]:
        with self.session_local() as db:
            now = datetime.now(timezone.utc)
            rows = (
                db.query(VaultIndex)
                .filter(
                    VaultIndex.index_after <= now,
                    or_(VaultIndex.status_index == "READY", VaultIndex.status_index == "RETRY"),
                )
                .order_by(VaultIndex.index_after.asc())
                .limit(DB_BATCH_SIZE)
                .all()
            )
            for row in rows:
                db.expunge(row)
                yield row

    def _iter_rows_for_vault(self, username: str, vault_id: int) -> list[VaultIndex]:
        with self.session_local() as db:
            rows = (
                db.query(VaultIndex)
                .filter(VaultIndex.username == username)
                .order_by(VaultIndex.updated_at.desc())
                .all()
            )
            result: list[VaultIndex] = []
            for row in rows:
                if _vault_id_matches(username=row.username, vault_path=row.vault_path, vault_id=vault_id):
                    db.expunge(row)
                    result.append(row)
            return result

    def _process_row(self, row: VaultIndex) -> None:
        with self.session_local() as db:
            current = db.query(VaultIndex).filter(VaultIndex.id == row.id).first()
            if current is None:
                return

            current.status_index = "PROCESSING"
            current.processing_status = "indexing"
            current.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(current)

            try:
                self._upsert_document(current)
                current.status_index = "INDEXED"
                current.processing_status = "indexed"
                current.updated_at = datetime.now(timezone.utc)
                db.commit()
            except SkipIndexError as exc:
                logger.info("Skip indexing for id=%s path=%s: %s", current.id, current.vault_path, exc)
                current.status_index = "SKIPPED"
                current.processing_status = str(exc)
                current.updated_at = datetime.now(timezone.utc)
                db.commit()
            except Exception as exc:
                logger.exception("Failed to index file id=%s path=%s", current.id, current.vault_path)
                current.status_index = "RETRY"
                current.processing_status = f"index_error:{type(exc).__name__}"
                current.index_after = datetime.now(timezone.utc) + timedelta(minutes=RETRY_AFTER_MINUTES)
                current.updated_at = datetime.now(timezone.utc)
                db.commit()

    def _upsert_document(self, row: VaultIndex) -> None:
        if not row.minio_object_name or not row.minio_bucket_name:
            raise RuntimeError("MinIO object or bucket is missing")
        if not self._should_index_row(row):
            raise SkipIndexError("skip_non_text_or_media")

        payload = self._download_minio_object(row.minio_bucket_name, row.minio_object_name)
        if len(payload) > MAX_SOURCE_TEXT_BYTES:
            raise SkipIndexError("skip_too_large_source")
        text_value = payload.decode("utf-8", errors="ignore")
        if not text_value.strip():
            raise SkipIndexError("skip_empty_after_decode")

        chunks = split_text(text_value)
        if not chunks:
            raise RuntimeError("Document was split into zero chunks")

        user_settings = self._load_user_llm_settings_by_user_id(row.user_id)
        vectors = self.embeddings.embed_many(
            chunks,
            openrouter_api_key=str(user_settings.get("openrouter_api_key", "") or ""),
            openrouter_model=OPENROUTER_EMBED_MODEL,
            provider="openrouter",
        )
        if len(vectors) != len(chunks):
            raise RuntimeError("Embeddings/chunks length mismatch")

        self._ensure_qdrant_collection(vector_size=len(vectors[0]))
        doc_key = f"{row.username}::{row.vault_path}"
        vault_id = _stable_vault_id(row.username, _vault_root_from_path(row.vault_path))
        self._delete_points_for_doc(doc_key)

        points: list[PointStruct] = []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
            point_id = str(uuid.uuid4())
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "username": row.username,
                        "vault_path": row.vault_path,
                        "doc_key": doc_key,
                        "vault_id": vault_id,
                        "chunk_index": idx,
                        "content_hash": row.content_hash,
                        "source_bucket": row.minio_bucket_name,
                        "source_object": row.minio_object_name,
                        "text": chunk,
                        "indexed_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
        for i in range(0, len(points), QDRANT_UPSERT_BATCH_SIZE):
            batch = points[i : i + QDRANT_UPSERT_BATCH_SIZE]
            self.qdrant_client.upsert(collection_name=QDRANT_COLLECTION, points=batch, wait=True)

    @staticmethod
    def _should_index_row(row: VaultIndex) -> bool:
        if row.minio_bucket_name and row.minio_bucket_name.endswith("-media"):
            return False
        lower_path = (row.vault_path or "").lower()
        return lower_path.endswith(".md") or lower_path.endswith(".txt")

    def _download_minio_object(self, bucket_name: str, object_name: str) -> bytes:
        response = self.minio_client.get_object(bucket_name=bucket_name, object_name=object_name)
        try:
            buffer = BytesIO()
            for data in response.stream(32 * 1024):
                buffer.write(data)
            return buffer.getvalue()
        finally:
            response.close()
            response.release_conn()

    def _delete_points_for_doc(self, doc_key: str) -> None:
        self.qdrant_client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=Filter(
                must=[FieldCondition(key="doc_key", match=MatchValue(value=doc_key))]
            ),
            wait=True,
        )

    def _ensure_qdrant_collection(self, vector_size: int = EMBEDDING_DIM) -> None:
        collections = self.qdrant_client.get_collections().collections
        if any(c.name == QDRANT_COLLECTION for c in collections):
            info = self.qdrant_client.get_collection(collection_name=QDRANT_COLLECTION)
            existing_dim = _read_qdrant_vector_size(info)
            if existing_dim is not None and existing_dim != vector_size:
                logger.warning(
                    "Qdrant collection '%s' has dim=%s but current embeddings need dim=%s; "
                    "deleting collection (all vectors will be reindexed)",
                    QDRANT_COLLECTION,
                    existing_dim,
                    vector_size,
                )
                self.qdrant_client.delete_collection(collection_name=QDRANT_COLLECTION)
            else:
                return
        self.qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("Created Qdrant collection '%s' with dim=%s", QDRANT_COLLECTION, vector_size)

    def _ensure_llm_tokens_table(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS llm_tokens (
                        user_id INTEGER PRIMARY KEY,
                        input_tokens INTEGER NOT NULL DEFAULT 0,
                        output_tokens INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )
            )

    def _ensure_user_llm_settings_table(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS user_llm_settings (
                        user_id INTEGER PRIMARY KEY,
                        openrouter_api_key TEXT NOT NULL DEFAULT '',
                        openrouter_llm_model TEXT NOT NULL DEFAULT 'google/gemini-3-flash-preview',
                        openrouter_deep_research_model TEXT NOT NULL DEFAULT 'perplexity/sonar-deep-research',
                        temperature DOUBLE PRECISION NOT NULL DEFAULT 0.2,
                        top_p DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                        presence_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                        frequency_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                        max_tokens INTEGER NOT NULL DEFAULT 900,
                        deep_research_temperature DOUBLE PRECISION NOT NULL DEFAULT 0.1,
                        deep_research_top_p DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                        deep_research_presence_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                        deep_research_frequency_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                        deep_research_max_tokens INTEGER NOT NULL DEFAULT 1600,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )

    def _load_user_llm_settings_by_user_id(self, user_id: int | None) -> dict[str, Any]:
        if user_id is None:
            return dict(DEFAULT_LLM_SETTINGS)
        with self.session_local() as db:
            row = db.execute(
                text(
                    """
                    SELECT
                        openrouter_api_key,
                        openrouter_llm_model,
                        openrouter_deep_research_model,
                        temperature,
                        top_p,
                        presence_penalty,
                        frequency_penalty,
                        max_tokens,
                        deep_research_temperature,
                        deep_research_top_p,
                        deep_research_presence_penalty,
                        deep_research_frequency_penalty,
                        deep_research_max_tokens
                    FROM user_llm_settings
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": user_id},
            ).first()
        if row is None:
            return dict(DEFAULT_LLM_SETTINGS)
        return {
            "openrouter_api_key": str(row[0] or ""),
            "openrouter_llm_model": str(row[1] or OPENROUTER_LLM_MODEL),
            "openrouter_deep_research_model": str(row[2] or OPENROUTER_DEEP_RESEARCH_MODEL),
            "temperature": float(row[3] if row[3] is not None else DEFAULT_LLM_SETTINGS["temperature"]),
            "top_p": float(row[4] if row[4] is not None else DEFAULT_LLM_SETTINGS["top_p"]),
            "presence_penalty": float(row[5] if row[5] is not None else DEFAULT_LLM_SETTINGS["presence_penalty"]),
            "frequency_penalty": float(row[6] if row[6] is not None else DEFAULT_LLM_SETTINGS["frequency_penalty"]),
            "max_tokens": int(row[7] if row[7] is not None else DEFAULT_LLM_SETTINGS["max_tokens"]),
            "deep_research_temperature": float(
                row[8] if row[8] is not None else DEFAULT_LLM_SETTINGS["deep_research_temperature"]
            ),
            "deep_research_top_p": float(
                row[9] if row[9] is not None else DEFAULT_LLM_SETTINGS["deep_research_top_p"]
            ),
            "deep_research_presence_penalty": float(
                row[10] if row[10] is not None else DEFAULT_LLM_SETTINGS["deep_research_presence_penalty"]
            ),
            "deep_research_frequency_penalty": float(
                row[11] if row[11] is not None else DEFAULT_LLM_SETTINGS["deep_research_frequency_penalty"]
            ),
            "deep_research_max_tokens": int(
                row[12] if row[12] is not None else DEFAULT_LLM_SETTINGS["deep_research_max_tokens"]
            ),
        }

    def get_stats(self) -> VaultStats:
        collection_info = self.qdrant_client.get_collection(collection_name=QDRANT_COLLECTION)
        total_points = collection_info.points_count or 0
        unique_files: set[str] = set()
        unique_users: set[str] = set()
        chunks_by_user: dict[str, int] = {}

        next_page = None
        while True:
            points, next_page = self.qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION,
                limit=1000,
                offset=next_page,
                with_payload=True,
            )
            for point in points:
                payload = point.payload or {}
                username = str(payload.get("username", "unknown"))
                doc_key = str(payload.get("doc_key", ""))
                if doc_key:
                    unique_files.add(doc_key)
                unique_users.add(username)
                chunks_by_user[username] = chunks_by_user.get(username, 0) + 1
            if next_page is None:
                break

        return VaultStats(
            collection=QDRANT_COLLECTION,
            total_points=int(total_points),
            unique_files=len(unique_files),
            unique_users=len(unique_users),
            chunks_by_user=chunks_by_user,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_vaults(self, username: str) -> list[VaultSchema]:
        with self.session_local() as db:
            rows = (
                db.query(VaultIndex)
                .filter(VaultIndex.username == username)
                .order_by(VaultIndex.updated_at.desc())
                .all()
            )
        if not rows:
            return []

        root = "default"
        latest_row = max(rows, key=lambda item: item.updated_at)
        created_at = min((item.created_at for item in rows), default=latest_row.created_at)

        return [
            VaultSchema(
                id=_stable_vault_id(username, root),
                user_id=latest_row.user_id or 0,
                name=root,
                path=root,
                status="ready",
                created_at=created_at.isoformat(),
                updated_at=latest_row.updated_at.isoformat(),
            )
        ]

    def get_vault_by_id(self, username: str, vault_id: int) -> VaultSchema | None:
        with self.session_local() as db:
            rows = (
                db.query(VaultIndex)
                .filter(VaultIndex.username == username)
                .order_by(VaultIndex.updated_at.desc())
                .all()
            )
        if not rows:
            return None

        if not any(_vault_id_matches(username=username, vault_path=row.vault_path, vault_id=vault_id) for row in rows):
            return None

        root = "default"
        latest_row = max(rows, key=lambda item: item.updated_at)
        created_at = min((item.created_at for item in rows), default=latest_row.created_at)
        return VaultSchema(
            id=_stable_vault_id(username, root),
            user_id=latest_row.user_id or 0,
            name=root,
            path=root,
            status="ready",
            created_at=created_at.isoformat(),
            updated_at=latest_row.updated_at.isoformat(),
        )

    def get_index_info(self, username: str, vault_id: int) -> IndexInfoResponse:
        rows = self._iter_rows_for_vault(username=username, vault_id=vault_id)
        now = datetime.now(timezone.utc)
        ready_count = sum(1 for row in rows if row.status_index in {"READY", "RETRY"} and row.index_after <= now)
        all_docs = sum(1 for row in rows if self._should_index_row(row) and row.minio_object_name and row.minio_bucket_name)
        indexed_rows = [row for row in rows if row.status_index == "INDEXED"]
        last_update_time = max((row.updated_at for row in indexed_rows), default=None)
        progress_key = f"{username}:{vault_id}"
        progress = self.get_progress(progress_key)
        return IndexInfoResponse(
            n_documents_to_update=ready_count,
            n_all_documents=all_docs,
            last_update_time=last_update_time.isoformat() if last_update_time else None,
            in_update_process=progress.in_progress,
        )

    def get_progress(self, progress_key: str) -> UpdateIndexProgressResponse:
        with self._progress_lock:
            return self._progress_by_key.get(progress_key, UpdateIndexProgressResponse(in_progress=False, stages=[]))

    def _set_progress(self, progress_key: str, value: UpdateIndexProgressResponse) -> None:
        with self._progress_lock:
            self._progress_by_key[progress_key] = value

    def _set_stage_value(self, progress_key: str, stage_idx: int, value: int) -> None:
        with self._progress_lock:
            current = self._progress_by_key.get(progress_key)
            if current is None:
                return
            if stage_idx >= len(current.stages):
                return
            current.stages[stage_idx].value = max(0, min(100, value))

    def get_clusters(self, username: str, vault_id: int) -> ClustersResponse:
        rows = self._iter_rows_for_vault(username=username, vault_id=vault_id)
        by_doc: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not self._should_index_row(row):
                continue
            doc_key = f"{row.username}::{row.vault_path}"
            by_doc[doc_key] = {"name": row.vault_path, "x": 0.0, "y": 0.0, "has_points": False}

        # Получаем все точки для данного username из Qdrant
        # Фильтруем по username в payload
        all_points = []
        next_page = None
        while True:
            points, next_page = self.qdrant_client.scroll(
                collection_name=QDRANT_COLLECTION,
                scroll_filter=Filter(must=[FieldCondition(key="username", match=MatchValue(value=username))]),
                with_vectors=True,
                with_payload=True,
                limit=1000,
                offset=next_page,
            )
            if not points:
                break
            all_points.extend(points)
            if next_page is None:
                break

        # Группируем точки по doc_key и вычисляем средние координаты
        points_by_doc: dict[str, list[Any]] = {}
        for point in all_points:
            payload = point.payload or {}
            doc_key_from_point = str(payload.get("doc_key", ""))
            if doc_key_from_point in by_doc:
                if doc_key_from_point not in points_by_doc:
                    points_by_doc[doc_key_from_point] = []
                points_by_doc[doc_key_from_point].append(point)

        # Вычисляем координаты для каждого документа
        for doc_key, points_list in points_by_doc.items():
            if not points_list:
                continue
            xs = []
            ys = []
            for point in points_list:
                if isinstance(point.vector, list) and len(point.vector) > 0:
                    xs.append(point.vector[0])
                if isinstance(point.vector, list) and len(point.vector) > 1:
                    ys.append(point.vector[1])
            if xs:
                by_doc[doc_key]["x"] = float(sum(xs) / len(xs))
                by_doc[doc_key]["has_points"] = True
            if ys:
                by_doc[doc_key]["y"] = float(sum(ys) / len(ys))

        # Создаем кластеры только для документов с точками
        clusters = [
            ClusterSchema(
                name=item["name"].split("/")[-1].replace(".md", "").replace(".txt", ""),
                x=item["x"],
                y=item["y"],
            )
            for item in by_doc.values()
            if item["has_points"]
        ]
        return ClustersResponse(clusters=clusters)

    def delete_index_for_vault(self, username: str, vault_id: int) -> int:
        rows = self._iter_rows_for_vault(username=username, vault_id=vault_id)
        deleted_docs = 0
        for row in rows:
            doc_key = f"{row.username}::{row.vault_path}"
            self._delete_points_for_doc(doc_key)
            deleted_docs += 1
            with self.session_local() as db:
                current = db.query(VaultIndex).filter(VaultIndex.id == row.id).first()
                if current:
                    current.status_index = "READY"
                    current.processing_status = "index_deleted"
                    current.updated_at = datetime.now(timezone.utc)
                    db.commit()
        return deleted_docs

    def delete_vault(self, username: str, vault_id: int) -> int:
        rows = self._iter_rows_for_vault(username=username, vault_id=vault_id)
        if not rows:
            return 0
        row_ids = [row.id for row in rows]
        for row in rows:
            doc_key = f"{row.username}::{row.vault_path}"
            self._delete_points_for_doc(doc_key)
        with self.session_local() as db:
            db.query(VaultIndex).filter(VaultIndex.id.in_(row_ids)).delete(synchronize_session=False)
            db.commit()
        return len(rows)

    def get_file(self, username: str, vault_id: int, filename: str) -> VaultFileResponse:
        rows = self._iter_rows_for_vault(username=username, vault_id=vault_id)
        matched = [
            row
            for row in rows
            if row.vault_path.replace("\\", "/").split("/")[-1].lower() == filename.lower()
            and row.minio_bucket_name
            and row.minio_object_name
        ]
        if not matched:
            raise HTTPException(status_code=404, detail="File not found in vault")
        row = sorted(matched, key=lambda x: x.updated_at, reverse=True)[0]
        payload = self._download_minio_object(row.minio_bucket_name or "", row.minio_object_name or "")
        return VaultFileResponse(
            filename=filename,
            content=payload.decode("utf-8", errors="ignore"),
            path=row.vault_path,
        )


class SkipIndexError(Exception):
    pass


indexer = CoreIndexer()
chat_llm_service = OpenRouterLLMService()
chat_agent = VaultChatAgent(indexer.embeddings, indexer.qdrant_client, chat_llm_service)
app_object = FastAPI(title="core", docs_url="/docs", openapi_url="/openapi.json")


def _load_recent_chat_history(db: Any, chat_id: int, limit: int = RAG_AGENT_HISTORY_MESSAGES) -> list[dict[str, str]]:
    history_rows = (
        db.query(MessageModel)
        .filter(MessageModel.chat_id == chat_id)
        .order_by(MessageModel.created_date.desc())
        .limit(limit)
        .all()
    )
    history_rows.reverse()
    return [{"role": row.role, "content": row.content} for row in history_rows]


def _upsert_llm_tokens(db: Any, user_id: int, input_tokens: int, output_tokens: int) -> None:
    if input_tokens <= 0 and output_tokens <= 0:
        return
    try:
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS llm_tokens (
                    user_id INTEGER PRIMARY KEY,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        existing = db.execute(
            text("SELECT user_id FROM llm_tokens WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).first()
        if existing is None:
            db.execute(
                text(
                    "INSERT INTO llm_tokens (user_id, input_tokens, output_tokens) "
                    "VALUES (:user_id, :input_tokens, :output_tokens)"
                ),
                {
                    "user_id": user_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )
        else:
            db.execute(
                text(
                    "UPDATE llm_tokens SET "
                    "input_tokens = input_tokens + :input_tokens, "
                    "output_tokens = output_tokens + :output_tokens "
                    "WHERE user_id = :user_id"
                ),
                {
                    "user_id": user_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Failed to update llm_tokens table: %s", exc)


def _read_llm_tokens(db: Any, user_id: int) -> LLMTokensResponse:
    try:
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS llm_tokens (
                    user_id INTEGER PRIMARY KEY,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0
                )
                """
            )
        )
        row = db.execute(
            text("SELECT input_tokens, output_tokens FROM llm_tokens WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).first()
        if row is None:
            return LLMTokensResponse(input_tokens=0, output_tokens=0)
        return LLMTokensResponse(input_tokens=int(row[0]), output_tokens=int(row[1]))
    except Exception as exc:
        logger.warning("Failed to read llm_tokens table, returning zero counters: %s", exc)
        return LLMTokensResponse(input_tokens=0, output_tokens=0)


def _ensure_user_llm_settings_table(db: Any) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS user_llm_settings (
                user_id INTEGER PRIMARY KEY,
                openrouter_api_key TEXT NOT NULL DEFAULT '',
                openrouter_llm_model TEXT NOT NULL DEFAULT 'google/gemini-3-flash-preview',
                openrouter_deep_research_model TEXT NOT NULL DEFAULT 'perplexity/sonar-deep-research',
                temperature DOUBLE PRECISION NOT NULL DEFAULT 0.2,
                top_p DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                presence_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                frequency_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                max_tokens INTEGER NOT NULL DEFAULT 900,
                deep_research_temperature DOUBLE PRECISION NOT NULL DEFAULT 0.1,
                deep_research_top_p DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                deep_research_presence_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                deep_research_frequency_penalty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                deep_research_max_tokens INTEGER NOT NULL DEFAULT 1600,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )


def _sanitize_llm_settings_payload(payload: LLMSettingsRequest) -> dict[str, Any]:
    max_tokens = max(64, min(32000, int(payload.max_tokens)))
    deep_max_tokens = max(64, min(64000, int(payload.deep_research_max_tokens)))

    return {
        "openrouter_api_key": payload.openrouter_api_key.strip(),
        "openrouter_llm_model": payload.openrouter_llm_model.strip() or OPENROUTER_LLM_MODEL,
        "openrouter_deep_research_model": payload.openrouter_deep_research_model.strip() or OPENROUTER_DEEP_RESEARCH_MODEL,
        "temperature": max(0.0, min(2.0, float(payload.temperature))),
        "top_p": max(0.0, min(1.0, float(payload.top_p))),
        "presence_penalty": max(-2.0, min(2.0, float(payload.presence_penalty))),
        "frequency_penalty": max(-2.0, min(2.0, float(payload.frequency_penalty))),
        "max_tokens": max_tokens,
        "deep_research_temperature": max(0.0, min(2.0, float(payload.deep_research_temperature))),
        "deep_research_top_p": max(0.0, min(1.0, float(payload.deep_research_top_p))),
        "deep_research_presence_penalty": max(-2.0, min(2.0, float(payload.deep_research_presence_penalty))),
        "deep_research_frequency_penalty": max(-2.0, min(2.0, float(payload.deep_research_frequency_penalty))),
        "deep_research_max_tokens": deep_max_tokens,
    }


def _read_user_llm_settings(db: Any, user_id: int) -> dict[str, Any]:
    _ensure_user_llm_settings_table(db)
    row = db.execute(
        text(
            """
            SELECT
                openrouter_api_key,
                openrouter_llm_model,
                openrouter_deep_research_model,
                temperature,
                top_p,
                presence_penalty,
                frequency_penalty,
                max_tokens,
                deep_research_temperature,
                deep_research_top_p,
                deep_research_presence_penalty,
                deep_research_frequency_penalty,
                deep_research_max_tokens
            FROM user_llm_settings
            WHERE user_id = :user_id
            """
        ),
        {"user_id": user_id},
    ).first()
    if row is None:
        return dict(DEFAULT_LLM_SETTINGS)

    return {
        "openrouter_api_key": str(row[0] or ""),
        "openrouter_llm_model": str(row[1] or OPENROUTER_LLM_MODEL),
        "openrouter_deep_research_model": str(row[2] or OPENROUTER_DEEP_RESEARCH_MODEL),
        "temperature": float(row[3] if row[3] is not None else DEFAULT_LLM_SETTINGS["temperature"]),
        "top_p": float(row[4] if row[4] is not None else DEFAULT_LLM_SETTINGS["top_p"]),
        "presence_penalty": float(row[5] if row[5] is not None else DEFAULT_LLM_SETTINGS["presence_penalty"]),
        "frequency_penalty": float(row[6] if row[6] is not None else DEFAULT_LLM_SETTINGS["frequency_penalty"]),
        "max_tokens": int(row[7] if row[7] is not None else DEFAULT_LLM_SETTINGS["max_tokens"]),
        "deep_research_temperature": float(
            row[8] if row[8] is not None else DEFAULT_LLM_SETTINGS["deep_research_temperature"]
        ),
        "deep_research_top_p": float(
            row[9] if row[9] is not None else DEFAULT_LLM_SETTINGS["deep_research_top_p"]
        ),
        "deep_research_presence_penalty": float(
            row[10] if row[10] is not None else DEFAULT_LLM_SETTINGS["deep_research_presence_penalty"]
        ),
        "deep_research_frequency_penalty": float(
            row[11] if row[11] is not None else DEFAULT_LLM_SETTINGS["deep_research_frequency_penalty"]
        ),
        "deep_research_max_tokens": int(
            row[12] if row[12] is not None else DEFAULT_LLM_SETTINGS["deep_research_max_tokens"]
        ),
    }


def _upsert_user_llm_settings(db: Any, user_id: int, payload: LLMSettingsRequest) -> None:
    _ensure_user_llm_settings_table(db)
    settings = _sanitize_llm_settings_payload(payload)
    existing = db.execute(
        text("SELECT user_id FROM user_llm_settings WHERE user_id = :user_id"),
        {"user_id": user_id},
    ).first()
    if existing is None:
        db.execute(
            text(
                """
                INSERT INTO user_llm_settings (
                    user_id,
                    openrouter_api_key,
                    openrouter_llm_model,
                    openrouter_deep_research_model,
                    temperature,
                    top_p,
                    presence_penalty,
                    frequency_penalty,
                    max_tokens,
                    deep_research_temperature,
                    deep_research_top_p,
                    deep_research_presence_penalty,
                    deep_research_frequency_penalty,
                    deep_research_max_tokens,
                    updated_at
                ) VALUES (
                    :user_id,
                    :openrouter_api_key,
                    :openrouter_llm_model,
                    :openrouter_deep_research_model,
                    :temperature,
                    :top_p,
                    :presence_penalty,
                    :frequency_penalty,
                    :max_tokens,
                    :deep_research_temperature,
                    :deep_research_top_p,
                    :deep_research_presence_penalty,
                    :deep_research_frequency_penalty,
                    :deep_research_max_tokens,
                    NOW()
                )
                """
            ),
            {"user_id": user_id, **settings},
        )
    else:
        db.execute(
            text(
                """
                UPDATE user_llm_settings SET
                    openrouter_api_key = :openrouter_api_key,
                    openrouter_llm_model = :openrouter_llm_model,
                    openrouter_deep_research_model = :openrouter_deep_research_model,
                    temperature = :temperature,
                    top_p = :top_p,
                    presence_penalty = :presence_penalty,
                    frequency_penalty = :frequency_penalty,
                    max_tokens = :max_tokens,
                    deep_research_temperature = :deep_research_temperature,
                    deep_research_top_p = :deep_research_top_p,
                    deep_research_presence_penalty = :deep_research_presence_penalty,
                    deep_research_frequency_penalty = :deep_research_frequency_penalty,
                    deep_research_max_tokens = :deep_research_max_tokens,
                    updated_at = NOW()
                WHERE user_id = :user_id
                """
            ),
            {"user_id": user_id, **settings},
        )
    db.commit()


def _check_llm_settings_availability(payload: LLMSettingsRequest) -> LLMAvailabilityResponse:
    try:
        sanitized = _sanitize_llm_settings_payload(payload)
        api_key = str(sanitized["openrouter_api_key"])
        if not api_key:
            return LLMAvailabilityResponse(is_available=False, error_message="openrouter_api_key is empty")

        test_llm = OpenRouterLLMService()
        test_llm.run(
            system_prompt="You are a healthcheck assistant.",
            user_prompt="Reply with: ok",
            temperature=0.0,
            max_tokens=8,
            model=str(sanitized["openrouter_llm_model"]),
            api_key=api_key,
        )
        test_llm.run(
            system_prompt="You are a healthcheck assistant.",
            user_prompt="Reply with: ok",
            temperature=0.0,
            max_tokens=8,
            model=str(sanitized["openrouter_deep_research_model"]),
            api_key=api_key,
        )

        indexer.embeddings.embed_many(
            ["healthcheck"],
            openrouter_api_key=api_key,
            openrouter_model=OPENROUTER_EMBED_MODEL,
            provider="openrouter",
        )
        return LLMAvailabilityResponse(is_available=True, error_message="")
    except Exception as exc:
        return LLMAvailabilityResponse(is_available=False, error_message=str(exc))


def _process_chat_message(
    *,
    user_message: QueryRequest,
    authorization: str | None,
    deep_research: bool,
) -> AnswerResponse:
    user_id = _extract_user_id_from_token(authorization)
    username = _extract_username_from_token(authorization)
    with indexer.session_local() as db:
        chat = db.query(ChatModel).filter(ChatModel.id == user_message.chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if not chat.title or chat.title.strip().lower() == "new chat":
            existing_messages_count = (
                db.query(MessageModel.id)
                .filter(MessageModel.chat_id == user_message.chat_id)
                .count()
            )
            if existing_messages_count == 0:
                chat.title = _derive_chat_title_from_message(user_message.content)

        vault = indexer.get_vault_by_id(username=username, vault_id=user_message.vault_id)
        if vault is None:
            raise HTTPException(status_code=404, detail="Vault not found")

        history = _load_recent_chat_history(db=db, chat_id=user_message.chat_id)

        user_msg = MessageModel(
            chat_id=user_message.chat_id,
            content=user_message.content,
            role="user",
            created_date=datetime.now(timezone.utc),
        )
        db.add(user_msg)
        db.commit()

        user_settings = _read_user_llm_settings(db, user_id)

        answer, related_documents, fragments, used_tokens = chat_agent.run(
            username=username,
            vault_id=user_message.vault_id,
            user_query=user_message.content,
            chat_history=history,
            settings=user_settings,
            deep_research=deep_research,
        )

        serialized_fragments = [
            {
                "filename": fragment.filename,
                "text": fragment.text,
                "similarity": fragment.similarity,
                "chunk_id": fragment.chunk_id,
            }
            for fragment in fragments
        ]

        assistant_msg = MessageModel(
            chat_id=user_message.chat_id,
            content=answer,
            role="assistant",
            created_date=datetime.now(timezone.utc),
            fragments=json.dumps(serialized_fragments, ensure_ascii=False) if serialized_fragments else None,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        chat.updated_at = datetime.now(timezone.utc)
        db.commit()

        _upsert_llm_tokens(
            db=db,
            user_id=user_id,
            input_tokens=used_tokens[0],
            output_tokens=used_tokens[1],
        )

        return AnswerResponse(
            answer=answer,
            related_documents=related_documents,
            fragments=fragments,
            message_id=assistant_msg.id,
        )


@app_object.on_event("startup")
def on_startup() -> None:
    indexer.startup()


@app_object.on_event("shutdown")
def on_shutdown() -> None:
    indexer.shutdown()


@app_object.get("/healthcheck")
def healthcheck() -> dict[str, str | int]:
    return {
        "status": "ok",
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "delay_after_new_file_seconds": DELAY_AFTER_NEW_FILE_SECONDS,
        "max_new_file_workers": MAX_NEW_FILE_WORKERS,
    }


@app_object.post("/new_file")
def new_file(payload: NewFilePayload) -> dict[str, str]:
    _ = payload
    indexer.schedule_delayed_scan()
    return {
        "status": "accepted",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "scheduled_after_seconds": str(DELAY_AFTER_NEW_FILE_SECONDS),
    }


@app_object.post("/run_index_now")
def run_index_now() -> dict[str, str]:
    indexer.run_indexing_pass(reason="manual")
    return {"status": "ok", "triggered_at": datetime.now(timezone.utc).isoformat()}


@app_object.get("/stats", response_model=VaultStats)
def stats() -> VaultStats:
    return indexer.get_stats()


@app_object.get("/index_due_count")
def index_due_count() -> dict[str, int]:
    with indexer.session_local() as db:
        now = datetime.now(timezone.utc)
        count = (
            db.query(VaultIndex)
            .filter(
                VaultIndex.index_after <= now,
                or_(VaultIndex.status_index == "READY", VaultIndex.status_index == "RETRY"),
            )
            .count()
        )
    return {"due_count": count}


@app_object.get("/index/info/", response_model=IndexInfoResponse)
def index_info(
    vault_id: int = Query(..., description="Vault ID"),
    authorization: str | None = Header(default=None),
) -> IndexInfoResponse:
    username = _extract_username_from_token(authorization)
    return indexer.get_index_info(username=username, vault_id=vault_id)


@app_object.get("/index/clusters", response_model=ClustersResponse)
def index_clusters(
    vault_id: int = Query(..., description="Vault ID"),
    authorization: str | None = Header(default=None),
) -> ClustersResponse:
    username = _extract_username_from_token(authorization)
    return indexer.get_clusters(username=username, vault_id=vault_id)


@app_object.put("/index/", response_model=MessageResponse)
def index_update(
    vault_id: int = Query(..., description="Vault ID"),
    authorization: str | None = Header(default=None),
) -> MessageResponse:
    username = _extract_username_from_token(authorization)
    indexer.schedule_vault_reindex(username=username, vault_id=vault_id)
    return MessageResponse(message="The index update operation has started")


@app_object.get("/index/progress", response_model=UpdateIndexProgressResponse)
def index_progress(
    vault_id: int = Query(..., description="Vault ID"),
    authorization: str | None = Header(default=None),
) -> UpdateIndexProgressResponse:
    username = _extract_username_from_token(authorization)
    return indexer.get_progress(f"{username}:{vault_id}")


@app_object.delete("/index/", response_model=MessageResponse)
def index_delete(
    vault_id: int = Query(..., description="Vault ID"),
    authorization: str | None = Header(default=None),
) -> MessageResponse:
    username = _extract_username_from_token(authorization)
    deleted = indexer.delete_index_for_vault(username=username, vault_id=vault_id)
    return MessageResponse(message=f"Index deleted successfully ({deleted} documents)")


@app_object.get("/vaults/", response_model=VaultListResponse)
def vaults_list(authorization: str | None = Header(default=None)) -> VaultListResponse:
    username = _extract_username_from_token(authorization)
    return VaultListResponse(vaults=indexer.get_vaults(username=username))


@app_object.get("/vaults/{vault_id}", response_model=VaultSchema)
def vault_get(vault_id: int, authorization: str | None = Header(default=None)) -> VaultSchema:
    username = _extract_username_from_token(authorization)
    vault = indexer.get_vault_by_id(username=username, vault_id=vault_id)
    if vault is None:
        raise HTTPException(status_code=404, detail="Vault not found")
    return vault


@app_object.delete("/vaults/{vault_id}", response_model=MessageResponse)
def vault_delete(vault_id: int, authorization: str | None = Header(default=None)) -> MessageResponse:
    username = _extract_username_from_token(authorization)
    deleted = indexer.delete_vault(username=username, vault_id=vault_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Vault not found")
    return MessageResponse(message=f"Vault deleted successfully ({deleted} files)")


@app_object.post("/vaults/upload", response_model=MessageResponse)
def vault_upload_not_supported(authorization: str | None = Header(default=None)) -> MessageResponse:
    _ = _extract_username_from_token(authorization)
    raise HTTPException(
        status_code=501,
        detail="Vault ZIP upload is not supported in this architecture. Use Obsidian sync/file events pipeline.",
    )


@app_object.get("/vaults/{vault_id}/file/{filename:path}", response_model=VaultFileResponse)
def vault_get_file(vault_id: int, filename: str, authorization: str | None = Header(default=None)) -> VaultFileResponse:
    username = _extract_username_from_token(authorization)
    return indexer.get_file(username=username, vault_id=vault_id, filename=filename)


@app_object.get("/llm_tokens/", response_model=LLMTokensResponse)
def get_llm_tokens(authorization: str | None = Header(default=None)) -> LLMTokensResponse:
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        return _read_llm_tokens(db, user_id)


@app_object.get("/settings/llm/", response_model=LLMSettingsResponse)
def get_llm_settings(authorization: str | None = Header(default=None)) -> LLMSettingsResponse:
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        settings = _read_user_llm_settings(db, user_id)
        return LLMSettingsResponse(**settings)


@app_object.put("/settings/llm/", response_model=MessageResponse)
def update_llm_settings(
    payload: LLMSettingsRequest,
    authorization: str | None = Header(default=None),
) -> MessageResponse:
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        _upsert_user_llm_settings(db, user_id, payload)
    return MessageResponse(message="LLM settings updated successfully")


@app_object.post("/settings/llm/checking/", response_model=LLMAvailabilityResponse)
def check_llm_settings(payload: LLMSettingsRequest, authorization: str | None = Header(default=None)) -> LLMAvailabilityResponse:
    _ = _extract_user_id_from_token(authorization)
    return _check_llm_settings_availability(payload)


# Chats API
@app_object.post("/chats/", response_model=ChatResponse)
def create_chat(
    request: CreateChatRequest,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    """Создать новый чат"""
    user_id = _extract_user_id_from_token(authorization)
    username = _extract_username_from_token(authorization)
    title = request.title or "New Chat"
    vault_id: int | None = None
    if request.vault_id is not None:
        resolved_vault = indexer.get_vault_by_id(username=username, vault_id=request.vault_id)
        if resolved_vault is None:
            raise HTTPException(status_code=404, detail="Vault not found")
        vault_id = resolved_vault.id
    logger.info(f"Creating chat: user_id={user_id}, vault_id={vault_id}, title={title}")
    with indexer.session_local() as db:
        chat = ChatModel(
            user_id=user_id,
            vault_id=vault_id,
            title=title,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        logger.info(f"Chat created successfully: id={chat.id}")
        return ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            vault_id=chat.vault_id,
            title=chat.title,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )


@app_object.get("/chats/", response_model=ChatListResponse)
def list_chats(
    authorization: str | None = Header(default=None),
) -> ChatListResponse:
    """Получить список чатов пользователя"""
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        chats = db.query(ChatModel).filter(ChatModel.user_id == user_id).order_by(ChatModel.updated_at.desc()).all()
        return ChatListResponse(
            chats=[
                ChatResponse(
                    id=chat.id,
                    user_id=chat.user_id,
                    vault_id=chat.vault_id,
                    title=chat.title,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at,
                )
                for chat in chats
            ]
        )


@app_object.get("/chats/{chat_id}", response_model=ChatResponse)
def get_chat(
    chat_id: int,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    """Получить информацию о чате"""
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            vault_id=chat.vault_id,
            title=chat.title,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )


@app_object.put("/chats/{chat_id}", response_model=ChatResponse)
def update_chat(
    chat_id: int,
    request: UpdateChatRequest,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    """Обновить название чата"""
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        chat.title = request.title
        chat.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(chat)
        return ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            vault_id=chat.vault_id,
            title=chat.title,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )


@app_object.delete("/chats/{chat_id}", response_model=MessageResponse)
def delete_chat(
    chat_id: int,
    authorization: str | None = Header(default=None),
) -> MessageResponse:
    """Удалить чат"""
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        # Delete all messages in the chat
        db.query(MessageModel).filter(MessageModel.chat_id == chat_id).delete()
        db.delete(chat)
        db.commit()
        return MessageResponse(message="Chat deleted successfully")


# Messages API
@app_object.get("/messages/", response_model=MessageHistoryResponse)
def get_chat_messages(
    chat_id: int = Query(..., description="ID чата"),
    authorization: str | None = Header(default=None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> MessageHistoryResponse:
    """Получить историю сообщений чата"""
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        # Check chat access
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        messages = (
            db.query(MessageModel)
            .filter(MessageModel.chat_id == chat_id)
            .order_by(MessageModel.created_date.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        result_messages = []
        for msg in messages:
            fragments = []
            if msg.fragments:
                try:
                    fragments_data = json.loads(msg.fragments)
                    fragments = [FragmentInfoSchema(**f) if isinstance(f, dict) else f for f in fragments_data]
                except (json.JSONDecodeError, TypeError):
                    fragments = []
            
            result_messages.append(
                MessageSchema(
                    id=msg.id,
                    role=msg.role,
                    content=msg.content,
                    created_date=msg.created_date,
                    fragments=fragments,
                )
            )
        
        return MessageHistoryResponse(messages=result_messages)


@app_object.post("/messages/", response_model=AnswerResponse)
def post_user_message(
    user_message: QueryRequest,
    authorization: str | None = Header(default=None),
) -> AnswerResponse:
    """Отправить сообщение в чат и получить ответ agent-RAG."""
    return _process_chat_message(
        user_message=user_message,
        authorization=authorization,
        deep_research=False,
    )


@app_object.post("/messages/deep-research", response_model=AnswerResponse)
def post_deep_research_message(
    user_message: QueryRequest,
    authorization: str | None = Header(default=None),
) -> AnswerResponse:
    """Глубокий ответ по vault через perplexity/sonar-deep-research."""
    return _process_chat_message(
        user_message=user_message,
        authorization=authorization,
        deep_research=True,
    )


@app_object.post("/messages/combined", response_model=AnswerResponse)
def post_combined_search_message(
    user_message: QueryRequest,
    authorization: str | None = Header(default=None),
) -> AnswerResponse:
    """Legacy alias: forwards to deep-research mode."""
    return post_deep_research_message(user_message=user_message, authorization=authorization)


@app_object.delete("/messages/", response_model=MessageResponse)
def clean_message_history(
    chat_id: int = Query(..., description="ID чата"),
    authorization: str | None = Header(default=None),
) -> MessageResponse:
    """Очистить историю сообщений чата"""
    user_id = _extract_user_id_from_token(authorization)
    with indexer.session_local() as db:
        # Check chat access
        chat = db.query(ChatModel).filter(ChatModel.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        if chat.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        db.query(MessageModel).filter(MessageModel.chat_id == chat_id).delete()
        db.commit()
        return MessageResponse(message="Chat messages have been successfully deleted")

