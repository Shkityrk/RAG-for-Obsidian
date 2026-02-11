from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.database.models import UserModel
from src.repositories.user.interface import UserRepository


class UserSQLAlchemyRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, email: str, username: str, password_hash: str) -> dict:
        user = UserModel(
            email=email,
            username=username,
            password_hash=password_hash
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at
        }

    async def get_by_email(self, email: str) -> dict | None:
        statement = select(UserModel).where(UserModel.email == email)
        result = await self.session.execute(statement)
        user = result.scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "password_hash": user.password_hash
            }
        return None

    async def get_by_id(self, user_id: int) -> dict | None:
        statement = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(statement)
        user = result.scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "username": user.username
            }
        return None

