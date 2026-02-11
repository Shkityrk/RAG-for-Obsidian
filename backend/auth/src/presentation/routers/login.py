from fastapi import APIRouter, Depends, HTTPException, Response

from src.presentation.routers.dependences import get_auth_service
from src.schemas import schemas

from src.application.services.auth_service import AuthService

login_router = APIRouter()


@login_router.post("/login")
def login(
        response: Response,
        user_login: schemas.UserLogin,
        auth_service: AuthService = Depends(get_auth_service)
):
    user = auth_service.authenticate_user(user_login)
    if not user:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    access_token = auth_service.create_access_token(data={"sub": user.username, "role": user.user_role})
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return {
        "message": "Успешный вход",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_role": user.user_role,
        }
    }
