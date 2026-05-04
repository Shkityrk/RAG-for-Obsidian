import pytest
from fastapi import HTTPException
from jose import jwt

from src.core_utils import (
    extract_username_from_bearer_token,
    legacy_stable_vault_id,
    parse_json_object,
    split_text,
    stable_vault_id,
    vault_id_matches,
    derive_chat_title_from_message,
)


def test_split_text_normalizes_windows_newlines_and_overlaps_chunks() -> None:
    chunks = split_text("  abc\r\ndefghij  ", chunk_size=5, overlap=2)

    assert chunks == ["abc\nd", "\ndefg", "fghij"]


def test_split_text_returns_empty_list_for_blank_content() -> None:
    assert split_text(" \n\r\n ") == []


def test_stable_vault_id_is_deterministic_and_int32_safe() -> None:
    first = stable_vault_id("alice", "default")
    second = stable_vault_id("alice", "default")

    assert first == second
    assert 0 <= first <= 2_147_483_647


def test_vault_id_matches_current_and_legacy_candidates() -> None:
    assert vault_id_matches("alice", "notes/today.md", stable_vault_id("alice", "default"))
    assert vault_id_matches("alice", "notes/today.md", legacy_stable_vault_id("alice", "notes"))
    assert not vault_id_matches("alice", "notes/today.md", stable_vault_id("bob", "default"))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"answer": "ok"}', {"answer": "ok"}),
        ('```json\n{"answer": "ok"}\n```', {"answer": "ok"}),
        ('Here is the payload: {"answer": "ok"} thanks', {"answer": "ok"}),
        ("not json", {}),
    ],
)
def test_parse_json_object_accepts_plain_fenced_and_embedded_objects(
    raw: str,
    expected: dict[str, str],
) -> None:
    assert parse_json_object(raw) == expected


def test_derive_chat_title_collapses_whitespace_and_truncates() -> None:
    assert derive_chat_title_from_message("  one\n   two three  ", max_chars=8) == "one two"


def test_derive_chat_title_uses_default_for_blank_messages() -> None:
    assert derive_chat_title_from_message(" \n ", max_chars=48) == "New Chat"


def test_extract_username_from_bearer_token_reads_subject() -> None:
    token = jwt.encode({"sub": "alice"}, "secret", algorithm="HS256")

    assert extract_username_from_bearer_token(
        f"Bearer {token}",
        secret_key="secret",
        algorithm="HS256",
    ) == "alice"


@pytest.mark.parametrize("authorization", [None, "", "Basic token"])
def test_extract_username_from_bearer_token_rejects_missing_bearer(authorization: str | None) -> None:
    with pytest.raises(HTTPException) as exc_info:
        extract_username_from_bearer_token(
            authorization,
            secret_key="secret",
            algorithm="HS256",
        )

    assert exc_info.value.status_code == 401
