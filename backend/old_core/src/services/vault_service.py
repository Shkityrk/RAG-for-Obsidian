import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VaultService:
    """Сервис для работы с Obsidian волтами: распаковка, удаление и т.д."""

    def __init__(self, vaults_base_path: str):
        self.vaults_base_path = Path(vaults_base_path)
        self.vaults_base_path.mkdir(parents=True, exist_ok=True)

    def get_vault_path(self, user_id: int, vault_id: int) -> Path:
        """Получить путь к папке волта"""
        return self.vaults_base_path / f"user_{user_id}" / f"vault_{vault_id}"

    async def extract_zip(self, zip_path: str, user_id: int, vault_id: int) -> Path:
        """
        Распаковывает ZIP архив в папку волта.
        Возвращает путь к папке с .md файлами.
        """
        vault_path = self.get_vault_path(user_id, vault_id)
        vault_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Extracting ZIP {zip_path} to {vault_path}")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(vault_path)

        # Ищем все .md файлы рекурсивно во всех папках
        md_files = list(vault_path.rglob("*.md"))
        if md_files:
            # Всегда возвращаем корневой путь vault_path, так как rglob рекурсивно
            # находит все .md файлы во всех подпапках. Это позволяет правильно
            # обрабатывать vault с несколькими папками.
            logger.info(f"Found {len(md_files)} .md files in vault: {vault_path}")
            return vault_path

        logger.warning(f"No .md files found in vault {vault_path}")
        return vault_path

    async def delete_vault(self, user_id: int, vault_id: int) -> None:
        """Удаляет папку волта с диска"""
        vault_path = self.get_vault_path(user_id, vault_id)
        if vault_path.exists():
            shutil.rmtree(vault_path)
            logger.info(f"Deleted vault directory: {vault_path}")
        else:
            logger.warning(f"Vault directory does not exist: {vault_path}")

    async def get_vault_stats(self, vault_path: Path) -> dict:
        """Получить статистику по волту (количество файлов, размер и т.д.)"""
        if not vault_path.exists():
            return {"total_files": 0, "total_size": 0}

        md_files = list(vault_path.rglob("*.md"))
        total_size = sum(f.stat().st_size for f in md_files)

        return {
            "total_files": len(md_files),
            "total_size": total_size
        }

