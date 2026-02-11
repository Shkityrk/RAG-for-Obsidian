from fastapi import APIRouter, Depends, Request

from src.presentation.routers.dependences import get_auth_service
from src.schemas import schemas
from src.application.services.auth_service import AuthService

info_router = APIRouter()

@info_router.get("/info", response_model=schemas.UserOut)
def verify_token(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    token = auth_service.get_token_from_request(request)
    user = auth_service.get_current_user(token)
    return user
