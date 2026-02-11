from sqlalchemy.orm import Session
from fastapi import Depends

from src.application.services.auth_service import AuthService
from src.infrastructure.db.repositories.user import UserRepository
from src.infrastructure.db.session import get_db


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))