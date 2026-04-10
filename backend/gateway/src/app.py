import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware


def _get_list_env(name: str, default: str = "*") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8002")
FILE_CORE_URL = os.getenv("FILE_CORE_URL", "http://file_core:8003")
CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core:8005")
ORIGIN_URLS = _get_list_env("ORIGIN_URLS")


class AuthPayload(BaseModel):
    username: str
    password: str


class RegisterPayload(BaseModel):
    first_name: str
    last_name: str
    username: str
    email: str
    password: str
    user_role: str = "client"


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


app_object = FastAPI(title="gateway", docs_url="/docs", openapi_url="/openapi.json")
app_object.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGIN_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _proxy_request(
    method: str,
    url: str,
    json_data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.request(method=method, url=url, json=json_data, headers=headers)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}") from exc

    content_type = response.headers.get("content-type", "")
    payload: Any
    if "application/json" in content_type:
        payload = response.json()
    else:
        payload = {"raw": response.text}
    return JSONResponse(status_code=response.status_code, content=payload)


@app_object.get("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app_object.post("/api/auth/login")
async def login(payload: AuthPayload) -> JSONResponse:
    return await _proxy_request("POST", f"{AUTH_SERVICE_URL}/auth/login", json_data=payload.model_dump())


@app_object.post("/api/auth/register")
async def register(payload: RegisterPayload) -> JSONResponse:
    return await _proxy_request("POST", f"{AUTH_SERVICE_URL}/auth/register", json_data=payload.model_dump())


@app_object.get("/api/auth/info")
async def info(request: Request) -> JSONResponse:
    auth_header = request.headers.get("Authorization")
    headers = {"Authorization": auth_header} if auth_header else {}
    return await _proxy_request("GET", f"{AUTH_SERVICE_URL}/auth/info", headers=headers)


@app_object.post("/api/files/events")
async def file_events(payload: FileEventPayload, request: Request) -> JSONResponse:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header is required")
    
    # Логируем для отладки медиа-файлов
    if payload.is_media:
        media_size = len(payload.media_content_base64) if payload.media_content_base64 else 0
        print(f"[GATEWAY] Proxying media file: {payload.path}, size: {media_size} bytes (base64)")
    
    return await _proxy_request(
        "POST",
        f"{FILE_CORE_URL}/files/events",
        json_data=payload.model_dump(),
        headers={"Authorization": auth_header},
    )


async def _proxy_core_raw(request: Request, core_path: str) -> Response:
    auth_header = request.headers.get("Authorization")
    headers = {"Authorization": auth_header} if auth_header else {}
    query = request.url.query
    url = f"{CORE_SERVICE_URL}{core_path}"
    if query:
        url = f"{url}?{query}"

    json_data: dict[str, Any] | None = None
    if request.method in {"POST", "PUT", "PATCH"}:
        try:
            json_data = await request.json()
        except Exception:
            json_data = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            upstream = await client.request(method=request.method, url=url, json=json_data, headers=headers)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Core request failed: {exc}") from exc
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


@app_object.get("/api/index/info/")
async def index_info_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/index/info/")


@app_object.get("/api/index/clusters")
async def index_clusters_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/index/clusters")


@app_object.put("/api/index/")
async def index_update_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/index/")


@app_object.get("/api/index/progress")
async def index_progress_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/index/progress")


@app_object.delete("/api/index/")
async def index_delete_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/index/")


@app_object.get("/api/vaults/")
async def vaults_list_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/vaults/")


@app_object.get("/api/vaults/{vault_id}")
async def vault_get_proxy(vault_id: int, request: Request) -> Response:
    _ = vault_id
    return await _proxy_core_raw(request, f"/vaults/{vault_id}")


@app_object.delete("/api/vaults/{vault_id}")
async def vault_delete_proxy(vault_id: int, request: Request) -> Response:
    _ = vault_id
    return await _proxy_core_raw(request, f"/vaults/{vault_id}")


@app_object.post("/api/vaults/upload")
async def vault_upload_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/vaults/upload")


@app_object.get("/api/vaults/{vault_id}/file/{filename:path}")
async def vault_file_proxy(vault_id: int, filename: str, request: Request) -> Response:
    _ = vault_id
    _ = filename
    return await _proxy_core_raw(request, f"/vaults/{vault_id}/file/{filename}")


@app_object.get("/api/llm_tokens/")
async def llm_tokens_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/llm_tokens/")


@app_object.get("/api/settings/llm/")
async def settings_llm_get_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/settings/llm/")


@app_object.put("/api/settings/llm/")
async def settings_llm_put_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/settings/llm/")


@app_object.post("/api/settings/llm/checking/")
async def settings_llm_check_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/settings/llm/checking/")


@app_object.post("/api/chats/")
async def chats_create_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/chats/")


@app_object.get("/api/chats/")
async def chats_list_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/chats/")


@app_object.get("/api/chats/{chat_id}")
async def chats_get_proxy(chat_id: int, request: Request) -> Response:
    _ = chat_id
    return await _proxy_core_raw(request, f"/chats/{chat_id}")


@app_object.put("/api/chats/{chat_id}")
async def chats_update_proxy(chat_id: int, request: Request) -> Response:
    _ = chat_id
    return await _proxy_core_raw(request, f"/chats/{chat_id}")


@app_object.delete("/api/chats/{chat_id}")
async def chats_delete_proxy(chat_id: int, request: Request) -> Response:
    _ = chat_id
    return await _proxy_core_raw(request, f"/chats/{chat_id}")


@app_object.get("/api/messages/")
async def messages_list_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/messages/")


@app_object.post("/api/messages/")
async def messages_create_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/messages/")


@app_object.post("/api/messages/combined")
async def messages_combined_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/messages/combined")


@app_object.post("/api/messages/deep-research")
async def messages_deep_research_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/messages/deep-research")


@app_object.delete("/api/messages/")
async def messages_delete_proxy(request: Request) -> Response:
    return await _proxy_core_raw(request, "/messages/")

