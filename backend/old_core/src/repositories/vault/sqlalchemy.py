from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete

from src.database.models import VaultModel
from src.repositories.vault.interface import VaultRepository


class VaultSQLAlchemyRepository(VaultRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int, name: str, path: str, status: str = "ready") -> dict:
        vault = VaultModel(
            user_id=user_id,
            name=name,
            path=path,
            status=status
        )
        self.session.add(vault)
        await self.session.commit()
        await self.session.refresh(vault)
        return {
            "id": vault.id,
            "user_id": vault.user_id,
            "name": vault.name,
            "path": vault.path,
            "status": vault.status,
            "created_at": vault.created_at,
            "updated_at": vault.updated_at
        }

    async def get_by_user(self, user_id: int) -> list[dict]:
        statement = select(VaultModel).where(VaultModel.user_id == user_id)
        result = await self.session.execute(statement)
        vaults = result.scalars().all()
        return [
            {
                "id": vault.id,
                "user_id": vault.user_id,
                "name": vault.name,
                "path": vault.path,
                "status": vault.status,
                "created_at": vault.created_at,
                "updated_at": vault.updated_at
            }
            for vault in vaults
        ]

    async def get_by_id(self, vault_id: int) -> dict | None:
        statement = select(VaultModel).where(VaultModel.id == vault_id)
        result = await self.session.execute(statement)
        vault = result.scalar_one_or_none()
        if vault:
            return {
                "id": vault.id,
                "user_id": vault.user_id,
                "name": vault.name,
                "path": vault.path,
                "status": vault.status,
                "created_at": vault.created_at,
                "updated_at": vault.updated_at
            }
        return None

    async def update_status(self, vault_id: int, status: str) -> None:
        statement = (
            select(VaultModel)
            .where(VaultModel.id == vault_id)
        )
        result = await self.session.execute(statement)
        vault = result.scalar_one_or_none()
        if vault:
            vault.status = status
            await self.session.commit()
            await self.session.refresh(vault)

    async def update_path(self, vault_id: int, path: str) -> None:
        statement = (
            select(VaultModel)
            .where(VaultModel.id == vault_id)
        )
        result = await self.session.execute(statement)
        vault = result.scalar_one_or_none()
        if vault:
            vault.path = path
            await self.session.commit()
            await self.session.refresh(vault)

    async def delete(self, vault_id: int) -> None:
        statement = delete(VaultModel).where(VaultModel.id == vault_id)
        await self.session.execute(statement)
        await self.session.commit()

