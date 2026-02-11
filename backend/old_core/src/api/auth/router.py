from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth.dependencies import get_user_repository
from src.api.auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from src.api.auth.security import verify_password, get_password_hash, create_access_token
from src.database.session import get_async_session
from src.repositories.user.interface import UserRepository

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> TokenResponse:
    """Регистрация нового пользователя"""
    # Проверка существования пользователя
    existing_user = await user_repo.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Проверка username (можно добавить в репозиторий)
    # Пока пропускаем, так как в БД есть unique constraint
    
    # Создание пользователя
    password_hash = get_password_hash(request.password)
    user = await user_repo.create(
        email=request.email,
        username=request.username,
        password_hash=password_hash
    )
    
    # Создание токена
    access_token = create_access_token(data={"sub": str(user["id"])})
    
    return TokenResponse(
        access_token=access_token,
        user_id=user["id"],
        username=user["username"]
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> TokenResponse:
    """Вход пользователя"""
    user = await user_repo.get_by_email(request.email)
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user["id"])})
    
    return TokenResponse(
        access_token=access_token,
        user_id=user["id"],
        username=user["username"]
    )

