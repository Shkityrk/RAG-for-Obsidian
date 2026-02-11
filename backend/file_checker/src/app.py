import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from jose import JWTError, jwt
from minio import Minio
from pydantic import BaseModel
from sqlalchemy import DateTime, Integer, String, create_engine
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

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_NAME}"
)


class Base(DeclarativeBase):
    pass


class VaultIndex(Base):
    __tablename__ = quoted_name("index", True)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, index=True)
    minio_object_name: Mapped[str | None] = mapped_column(String, nullable=True)
    processing_status: Mapped[str] = mapped_column(String, nullable=False)
    vault_path: Mapped[str] = mapped_column(String, nullable=False)
    old_vault_path: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FileEventPayload(BaseModel):
    event_type: str
    path: str
    old_path: str | None = None
    content: str | None = None
    sha256: str | None = None
    timestamp: str


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
    Base.metadata.create_all(bind=engine)
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)


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


def _sanitize_filename(path: str) -> str:
    filename = path.split("/")[-1]
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in filename)


def _make_object_name(username: str, path: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{username}__{_sanitize_filename(path)}__{timestamp}"


def _upload_text_to_minio(object_name: str, content: str) -> None:
    payload_bytes = content.encode("utf-8")
    from io import BytesIO

    minio_client.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(payload_bytes),
        length=len(payload_bytes),
        content_type="text/markdown; charset=utf-8",
    )


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

    object_name: str | None = None
    status = "accepted"
    if payload.event_type in {"create", "modify"}:
        if payload.content is None:
            raise HTTPException(status_code=400, detail="content is required for create/modify events")
        object_name = _make_object_name(username, payload.path)
        _upload_text_to_minio(object_name, payload.content)
        status = "stored"
    elif payload.event_type == "delete":
        status = "deleted"
    elif payload.event_type == "rename":
        status = "renamed"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported event_type: {payload.event_type}")

    index_row = VaultIndex(
        username=username,
        minio_object_name=object_name,
        processing_status=status,
        vault_path=payload.path,
        old_vault_path=payload.old_path,
        event_type=payload.event_type,
        created_at=datetime.now(timezone.utc),
    )
    db.add(index_row)
    db.commit()

    return {"status": status, "username": username}

