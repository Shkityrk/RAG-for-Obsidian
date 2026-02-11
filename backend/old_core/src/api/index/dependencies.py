from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_async_session
from src.repositories.index.interface import FileRepository, UpdateProgressRepository
from src.repositories.index.sqlalchemy import FileSQLAlchemyRepository, UpdateProgressSQLAlchemyRepository
from src.services.index_service.base import BaseIndexService
from src.services.index_service.final import DemoIndexService


def get_file_repository(
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
) -> FileRepository:
    return FileSQLAlchemyRepository(db_session)


def get_update_progress_repository(
    db_session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UpdateProgressRepository:
    return UpdateProgressSQLAlchemyRepository(db_session)


def get_index_service_for_vault(
    vault_path: str,
    file_repository: Annotated[FileRepository, Depends(get_file_repository)],
    update_progress_repository: Annotated[UpdateProgressRepository, Depends(get_update_progress_repository)],
) -> BaseIndexService:
    """Создает IndexService для конкретного волта по его пути"""
    return DemoIndexService(
        obsidian_path=vault_path,
        file_repository=file_repository,
        update_progress_repository=update_progress_repository,
    )
