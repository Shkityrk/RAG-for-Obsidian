from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, desc, select, update

from src.database.models import FileModel, ProgressStageModel, UpdateProcessModel
from src.repositories.index.interface import FileRepository, UpdateProgressRepository


class FileSQLAlchemyRepository(FileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, vault_id: int, name: str, size: int, updated_at: datetime, x: float, y: float) -> None:
        file_record = FileModel(vault_id=vault_id, name=name, size=size, updated_at=updated_at, x=x, y=y)
        self.session.add(file_record)
        await self.session.commit()

    async def update(self, vault_id: int, name: str, size: int, updated_at: datetime, x: float, y: float) -> None:
        statement = select(FileModel).where(FileModel.vault_id == vault_id, FileModel.name == name)
        results = await self.session.execute(statement)
        file_record = results.first()

        if file_record is None:
            await self.add(
                vault_id=vault_id,
                name=name,
                size=size,
                updated_at=updated_at,
                x=x,
                y=y,
            )
        else:
            statement = (
                update(FileModel)
                .values(
                    name=name,
                    size=size,
                    updated_at=updated_at,
                    x=x,
                    y=y,
                )
                .where(FileModel.vault_id == vault_id, FileModel.name == name)
            )
            await self.session.execute(statement)
            await self.session.commit()

    async def remove_one(self, vault_id: int, name: str) -> None:
        statement = delete(FileModel).where(FileModel.vault_id == vault_id, FileModel.name == name)
        await self.session.execute(statement)
        await self.session.commit()

    async def remove(self, vault_id: int) -> None:
        statement = delete(FileModel).where(FileModel.vault_id == vault_id)
        await self.session.execute(statement)
        await self.session.commit()

    async def get_all(self, vault_id: int) -> list[dict]:
        statement = select(FileModel).where(FileModel.vault_id == vault_id)
        results = await self.session.execute(statement)
        files = results.scalars().all()
        return [file.model_dump() for file in files]


class UpdateProgressSQLAlchemyRepository(UpdateProgressRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_update_process(self, vault_id: int) -> int:
        new_process = UpdateProcessModel(vault_id=vault_id, started_at=datetime.utcnow(), is_actual=True)
        self.session.add(new_process)
        await self.session.flush()
        await self.session.refresh(new_process)
        return new_process.id

    async def get_update_process(self, vault_id: int) -> dict | None:
        statement = (
            select(UpdateProcessModel)
            .where(
                UpdateProcessModel.vault_id == vault_id,
                UpdateProcessModel.is_actual == True  # noqa: E712
            )
        )
        result = await self.session.execute(statement)
        process = result.scalars().first()
        return process and process.model_dump()

    async def get_last_update_process(self, vault_id: int) -> dict | None:
        statement = (
            select(UpdateProcessModel)
            .where(
                UpdateProcessModel.vault_id == vault_id,
                UpdateProcessModel.is_actual == False  # noqa: E712
            )
            .order_by(desc(UpdateProcessModel.finished_at))
            .limit(1)
        )
        result = await self.session.execute(statement)
        process = result.scalars().first()
        return process and process.model_dump()

    async def finish_update_process(self, process_id: int) -> None:
        statement = (
            update(UpdateProcessModel)
            .where(UpdateProcessModel.id == process_id)
            .values(finished_at=datetime.utcnow(), is_actual=False)
        )
        await self.session.execute(statement)
        await self.session.commit()
        await self.session.flush()  # Force flush to ensure changes are visible

    async def finish_all_active_processes(self, vault_id: int) -> int:
        """Finish all active processes for a vault. Returns number of processes finished."""
        statement = (
            update(UpdateProcessModel)
            .where(
                UpdateProcessModel.vault_id == vault_id,
                UpdateProcessModel.is_actual == True  # noqa: E712
            )
            .values(finished_at=datetime.utcnow(), is_actual=False)
        )
        result = await self.session.execute(statement)
        await self.session.commit()
        await self.session.flush()
        return result.rowcount or 0

    async def start_progress_stage(self, name: str, process_id: int) -> int:
        new_stage = ProgressStageModel(started_at=datetime.utcnow(), name=name, progress=0, process_id=process_id)
        self.session.add(new_stage)
        await self.session.commit()
        await self.session.refresh(new_stage)
        return new_stage.id

    async def get_stages_by_process(self, process_id: int) -> list[dict]:
        statement = select(ProgressStageModel).where(ProgressStageModel.process_id == process_id)
        result = await self.session.execute(statement)
        stages = result.scalars().all()
        return [stage.model_dump() for stage in stages]

    async def update_progress_stage(self, stage_id: int, progress: int) -> None:
        statement = select(ProgressStageModel).where(ProgressStageModel.id == stage_id)
        result = await self.session.execute(statement)
        progress_stage = result.scalars().first()
        if progress_stage is not None:
            progress_stage.progress = progress
            await self.session.commit()

    async def finish_progress_stage(self, stage_id: int) -> None:
        statement = (
            update(ProgressStageModel)
            .where(ProgressStageModel.id == stage_id)
            .values(finished_at=datetime.utcnow(), progress=100)
        )
        await self.session.execute(statement)
        await self.session.commit()
