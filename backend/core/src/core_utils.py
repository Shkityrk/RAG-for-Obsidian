import hashlib
import json
import re
from typing import Any

from fastapi import HTTPException
from jose import JWTError, jwt


INT32_MAX = 2_147_483_647


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


def extract_username_from_bearer_token(
    authorization: str | None,
    *,
    secret_key: str,
    algorithm: str,
) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization bearer token is required")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    username = payload.get("sub")
    if not isinstance(username, str) or not username:
        raise HTTPException(status_code=401, detail="Token does not contain username")
    return username


def vault_root_from_path(vault_path: str) -> str:
    _ = vault_path
    return "default"


def stable_vault_id(username: str, vault_root: str) -> int:
    digest = hashlib.sha1(f"{username}::{vault_root}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) & INT32_MAX


def legacy_stable_vault_id(username: str, vault_root: str) -> int:
    digest = hashlib.sha1(f"{username}::{vault_root}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def legacy_vault_root_from_path(vault_path: str) -> str:
    normalized = vault_path.replace("\\", "/").strip("/")
    if not normalized:
        return "default"
    return normalized.split("/")[0]


def vault_id_matches(username: str, vault_path: str, vault_id: int) -> bool:
    current_root = vault_root_from_path(vault_path)
    legacy_root = legacy_vault_root_from_path(vault_path)
    candidates = {
        stable_vault_id(username, current_root),
        legacy_stable_vault_id(username, current_root),
        stable_vault_id(username, legacy_root),
        legacy_stable_vault_id(username, legacy_root),
    }
    return vault_id in candidates


def read_qdrant_vector_size(collection_info: Any) -> int | None:
    try:
        params = collection_info.config.params
        if params is None:
            return None
        vectors = params.vectors
        if vectors is None:
            return None
        if isinstance(vectors, dict):
            for vector in vectors.values():
                if hasattr(vector, "size"):
                    return int(vector.size)
            return None
        if hasattr(vectors, "size"):
            return int(vectors.size)
    except Exception:
        return None
    return None


def parse_json_object(raw: str) -> dict[str, Any]:
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


def derive_chat_title_from_message(message_content: str, max_chars: int) -> str:
    normalized = " ".join(message_content.split()).strip()
    if not normalized:
        return "New Chat"
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()
