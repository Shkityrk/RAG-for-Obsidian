from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Request, status
from jose import jwt, JWTError

from src.config import (SECRET_KEY,
                        ALGORITHM,
                        ACCESS_TOKEN_EXPIRE_MINUTES)
from src.domain.interfaces.user_repository import AbstractUserRepository
from src.domain.models import User
from src.domain.utils import hash_password, verify_password
from src.schemas.schemas import UserCreate, UserLogin


class AuthService:
    def __init__(self, user_repo: AbstractUserRepository):
        self.user_repo = user_repo

    def register_user(self, user_data: UserCreate) -> User:
        existing_user = self.user_repo.get_by_username_or_email(
            username=user_data.username, email=user_data.email
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем или email уже существует",
            )

        hashed_pw = hash_password(user_data.password)

        # Используем роль из запроса или client по умолчанию
        user_role = user_data.user_role if user_data.user_role else "client"
        print(f"[AUTH SERVICE] Creating user with user_role = '{user_role}'")

        new_user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_pw,
            user_role=user_role,
        )
        saved_user = self.user_repo.save(new_user)
        return saved_user


    def authenticate_user(self, user_login: UserLogin) -> Optional[User]:
        user = self.user_repo.get_by_username(user_login.username)
        if not user or not verify_password(user_login.password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def get_current_user(self, token: str) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось проверить учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        user = self.user_repo.get_by_username(username)
        if user is None:
            raise credentials_exception
        return user

    @staticmethod
    def get_token_from_cookie(request: Request) -> str:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не удалось проверить токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if token.startswith("Bearer "):
            token = token[7:]
        return token

    @staticmethod
    def get_token_from_request(request: Request) -> str:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        return AuthService.get_token_from_cookie(request)