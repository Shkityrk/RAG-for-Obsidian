from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth.security import verify_token
from src.database.session import get_async_session
from src.repositories.user.interface import UserRepository
from src.repositories.user.sqlalchemy import UserSQLAlchemyRepository

security = HTTPBearer()


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_async_session)]
) -> UserRepository:
    return UserSQLAlchemyRepository(session)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)]
) -> dict:
    """Получает текущего авторизованного пользователя из JWT токена"""
    token = credentials.credentials
    # #region agent log
    import json
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"get_current_user called, token_preview: {token[:20] if token else None}")
    # #endregion
    payload = verify_token(token)
    # #region agent log
    logger.info(f"Token verification result: payload_valid={payload is not None}, user_id={payload.get('sub') if payload else None}")
    # #endregion
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id: int = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

