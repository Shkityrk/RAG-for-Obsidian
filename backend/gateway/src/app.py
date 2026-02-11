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
    return await _proxy_request(
        "POST",
        f"{FILE_CORE_URL}/files/events",
        json_data=payload.model_dump(),
        headers={"Authorization": auth_header},
    )

