from fastapi import APIRouter, Depends, Request

from src.presentation.routers.dependences import get_auth_service
from src.application.services.auth_service import AuthService

protected_route_router = APIRouter()


@protected_route_router.get("/protected-route")
def protected_route(
        request: Request,
        auth_service: AuthService = Depends(get_auth_service)
):
    token = auth_service.get_token_from_request(request)
    user = auth_service.get_current_user(token)
    return {"message": f"Привет, {user.username}!"}
