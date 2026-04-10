import base64
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from jose import JWTError, jwt
from minio import Minio
from pydantic import BaseModel
from sqlalchemy import (
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.sql import quoted_name


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_NAME = os.getenv("POSTGRES_NAME", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret")
AUTH_ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "vault-raw")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in {"1", "true"}
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core:8005")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_NAME}"
)


class Base(DeclarativeBase):
    pass


class VaultIndex(Base):
    __tablename__ = quoted_name("index", True)
    __table_args__ = (UniqueConstraint("username", "vault_path", name="uq_index_username_vault_path"),)

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


class VaultIndexHistory(Base):
    __tablename__ = "index_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vault_path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    previous_minio_object_name: Mapped[str] = mapped_column(String, nullable=False)
    previous_minio_bucket_name: Mapped[str | None] = mapped_column(String, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FileEventPayload(BaseModel):
    event_type: str
    path: str
    old_path: str | None = None
    content: str | None = None
    sha256: str | None = None
    timestamp: str
    is_media: bool = False
    media_content_base64: str | None = None
    media_content_type: str | None = None


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE,
)

app_object = FastAPI(title="file_core", docs_url="/docs", openapi_url="/openapi.json")


def _startup_setup() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        print("[STARTUP] Database tables created/verified")
        # Создаем ForeignKeyConstraint вручную после создания таблиц
        with engine.connect() as conn:
            try:
                # FK для index_history -> index
                conn.execute(
                    text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint 
                            WHERE conname = 'index_history_username_vault_path_fkey'
                        ) THEN
                            ALTER TABLE index_history
                            ADD CONSTRAINT index_history_username_vault_path_fkey
                            FOREIGN KEY (username, vault_path)
                            REFERENCES "index"(username, vault_path)
                            ON DELETE CASCADE;
                        END IF;
                    END $$;
                    """)
                )
                # FK для index.user_id -> users.id
                conn.execute(
                    text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint 
                            WHERE conname = 'index_user_id_fkey'
                        ) THEN
                            -- Проверяем, существует ли таблица users
                            IF EXISTS (
                                SELECT 1 FROM information_schema.tables 
                                WHERE table_name = 'users'
                            ) THEN
                                ALTER TABLE "index"
                                ADD CONSTRAINT index_user_id_fkey
                                FOREIGN KEY (user_id)
                                REFERENCES users(id)
                                ON DELETE CASCADE;
                            END IF;
                        END IF;
                    END $$;
                    """)
                )
                conn.commit()
                print("[STARTUP] ForeignKeyConstraints created/verified")
            except Exception as fk_exc:
                print(f"[STARTUP] Warning: Could not create FK constraints: {fk_exc}")
    except Exception as exc:
        print(f"[STARTUP] ERROR creating tables: {type(exc).__name__}: {exc}")
        raise
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
        print(f"[STARTUP] Created MinIO bucket: {MINIO_BUCKET}")


def _ensure_media_bucket(username: str) -> str:
    bucket_name = f"{username}-media"
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
    return bucket_name


@app_object.on_event("startup")
def on_startup() -> None:
    _startup_setup()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


def _get_user_id_by_username(db: Session, username: str) -> int | None:
    """Получить user_id из таблицы users по username"""
    result = db.execute(text("SELECT id FROM users WHERE username = :username"), {"username": username})
    row = result.first()
    return row[0] if row else None


def _sanitize_filename(path: str) -> str:
    filename = path.split("/")[-1]
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in filename)


def _make_object_name(username: str, path: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{username}__{_sanitize_filename(path)}__{timestamp}"


def _upload_text_to_minio(object_name: str, content: str) -> None:
    payload_bytes = content.encode("utf-8")
    minio_client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(payload_bytes),
        length=len(payload_bytes),
        content_type="text/markdown; charset=utf-8",
    )


def _upload_media_to_minio(username: str, object_name: str, media_content_base64: str, content_type: str) -> str:
    bucket_name = _ensure_media_bucket(username)
    try:
        media_bytes = base64.b64decode(media_content_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 media content: {exc}") from exc

    minio_client.put_object(
        bucket_name=bucket_name,
        object_name=object_name,
        data=BytesIO(media_bytes),
        length=len(media_bytes),
        content_type=content_type,
    )
    return bucket_name


def _core_payload(index_row: VaultIndex) -> dict[str, str]:
    return {
        "username": index_row.username,
        "vault_path": index_row.vault_path,
        "status_index": index_row.status_index,
        "minio_bucket_name": index_row.minio_bucket_name or "",
        "minio_object_name": index_row.minio_object_name or "",
    }


def _notify_core_new_file(index_row: VaultIndex) -> None:
    try:
        with httpx.Client(timeout=10.0) as client:
            client.post(f"{CORE_SERVICE_URL}/new_file", json=_core_payload(index_row))
    except httpx.HTTPError as exc:
        # Не заваливаем ingest, если core временно недоступен.
        print(f"core/new_file request failed: {exc}")


def _upsert_index_and_history(
    db: Session,
    username: str,
    payload: FileEventPayload,
    object_name: str | None,
    bucket_name: str | None,
    content_hash: str | None,
    processing_status: str,
) -> tuple[VaultIndex, bool]:
    now = datetime.now(timezone.utc)
    existing = (
        db.query(VaultIndex)
        .filter(VaultIndex.username == username, VaultIndex.vault_path == payload.path)
        .first()
    )
    print(f"[UPSERT] Existing record: {existing.id if existing else None}")

    # Получаем user_id из таблицы users
    user_id = _get_user_id_by_username(db, username)
    if user_id is None:
        print(f"[UPSERT] Warning: User '{username}' not found in users table")

    changed_content = False
    if existing is None:
        print(f"[UPSERT] Creating new record for {payload.path}")
        index_row = VaultIndex(
            user_id=user_id,
            username=username,
            minio_object_name=object_name,
            minio_bucket_name=bucket_name,
            content_hash=content_hash,
            processing_status=processing_status,
            status_index="READY",
            index_after=now + timedelta(minutes=5),
            vault_path=payload.path,
            old_vault_path=payload.old_path,
            event_type=payload.event_type,
            created_at=now,
            updated_at=now,
        )
        db.add(index_row)
        changed_content = payload.event_type in {"create", "modify"} and content_hash is not None
        return index_row, changed_content

    # Обновляем user_id если он изменился или был None
    if existing.user_id != user_id:
        existing.user_id = user_id

    existing.old_vault_path = payload.old_path
    existing.event_type = payload.event_type
    existing.processing_status = processing_status
    existing.updated_at = now

    if payload.event_type in {"create", "modify"} and content_hash is not None:
        if existing.content_hash != content_hash:
            print(f"[UPSERT] Content changed: old_hash={existing.content_hash}, new_hash={content_hash}")
            if existing.minio_object_name:
                db.add(
                    VaultIndexHistory(
                        username=existing.username,
                        vault_path=existing.vault_path,
                        previous_minio_object_name=existing.minio_object_name,
                        previous_minio_bucket_name=existing.minio_bucket_name,
                        changed_at=now,
                    )
                )
            existing.minio_object_name = object_name
            existing.minio_bucket_name = bucket_name
            existing.content_hash = content_hash
            existing.status_index = "READY"
            existing.index_after = now + timedelta(minutes=5)
            changed_content = True
        else:
            existing.processing_status = "unchanged"

    if payload.event_type == "rename" and payload.old_path:
        conflict = (
            db.query(VaultIndex)
            .filter(
                VaultIndex.username == username,
                VaultIndex.vault_path == payload.old_path,
                VaultIndex.id != existing.id,
            )
            .first()
        )
        if conflict is not None:
            raise HTTPException(status_code=409, detail="Duplicate vault_path for user on rename")

    return existing, changed_content


@app_object.get("/healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app_object.post("/files/events")
def ingest_file_event(
    payload: FileEventPayload,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    username = _extract_username_from_token(authorization)
    print(f"[INGEST] Received event: {payload.event_type} for {payload.path} by {username}")
    print(f"[INGEST] is_media={payload.is_media}, has_content={payload.content is not None}, has_media_base64={payload.media_content_base64 is not None}")
    if payload.is_media and payload.media_content_base64:
        media_size = len(payload.media_content_base64)
        print(f"[INGEST] Media file size (base64): {media_size} bytes (~{media_size * 3 // 4} bytes decoded)")

    object_name: str | None = None
    bucket_name: str | None = None
    content_hash: str | None = payload.sha256
    status = "accepted"
    if payload.event_type in {"create", "modify"} and payload.sha256 is None:
        raise HTTPException(status_code=400, detail="sha256 is required for create/modify events")

    if payload.event_type in {"create", "modify"}:
        existing = (
            db.query(VaultIndex)
            .filter(VaultIndex.username == username, VaultIndex.vault_path == payload.path)
            .first()
        )
        if existing is None or existing.content_hash != payload.sha256:
            object_name = _make_object_name(username, payload.path)
            if payload.is_media:
                if payload.media_content_base64 is None:
                    print(f"[INGEST] ERROR: media_content_base64 is None for media file {payload.path}")
                    raise HTTPException(
                        status_code=400,
                        detail="media_content_base64 is required for media files",
                    )
                if payload.media_content_type is None:
                    print(f"[INGEST] ERROR: media_content_type is None for media file {payload.path}")
                    raise HTTPException(
                        status_code=400,
                        detail="media_content_type is required for media files",
                    )
                try:
                    bucket_name = _upload_media_to_minio(
                        username, object_name, payload.media_content_base64, payload.media_content_type
                    )
                    status = "stored_media"
                    print(f"[INGEST] Successfully uploaded media to MinIO: {bucket_name}/{object_name}")
                except Exception as media_exc:
                    print(f"[INGEST] ERROR uploading media to MinIO: {type(media_exc).__name__}: {media_exc}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to upload media to MinIO: {media_exc}",
                    ) from media_exc
            else:
                if payload.content is None:
                    raise HTTPException(status_code=400, detail="content is required for create/modify events")
                _upload_text_to_minio(object_name, payload.content)
                bucket_name = MINIO_BUCKET
                status = "stored"
        else:
            status = "unchanged"
    elif payload.event_type == "delete":
        status = "deleted"
    elif payload.event_type == "rename":
        status = "renamed"
        old_index = (
            db.query(VaultIndex)
            .filter(VaultIndex.username == username, VaultIndex.vault_path == payload.old_path)
            .first()
        )
        if old_index is not None:
            conflict = (
                db.query(VaultIndex)
                .filter(VaultIndex.username == username, VaultIndex.vault_path == payload.path)
                .first()
            )
            if conflict is not None and conflict.id != old_index.id:
                raise HTTPException(status_code=409, detail="Target path already exists for user")
            # Обновляем user_id если нужно
            user_id = _get_user_id_by_username(db, username)
            if old_index.user_id != user_id:
                old_index.user_id = user_id
            old_index.vault_path = payload.path
            old_index.old_vault_path = payload.old_path
            old_index.event_type = payload.event_type
            old_index.processing_status = status
            old_index.updated_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": status, "username": username}
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported event_type: {payload.event_type}")

    try:
        index_row, changed_content = _upsert_index_and_history(
            db=db,
            username=username,
            payload=payload,
            object_name=object_name,
            bucket_name=bucket_name,
            content_hash=content_hash,
            processing_status=status,
        )
        print(f"[INGEST] Upsert completed: id={index_row.id}, changed_content={changed_content}")
        db.commit()
        db.refresh(index_row)
        print(f"[INGEST] Committed to DB: id={index_row.id}, status={status}")

        if changed_content:
            _notify_core_new_file(index_row)

        return {"status": status, "username": username}
    except Exception as exc:
        db.rollback()
        print(f"[INGEST] ERROR: {type(exc).__name__}: {exc}")
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc

