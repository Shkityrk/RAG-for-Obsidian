import logging
import os

import aiofiles

from src.repositories.index.interface import UpdateProgressRepository
from src.services.vector_store_service.base import BaseVectorStoreService
from src.utils.text_splitter import CustomTextSplitter

logger = logging.getLogger(__name__)


async def update_vector_store(
        vault_id: int,
        files_to_update: list[str],
        update_progress_repository: UpdateProgressRepository,
        vector_store: BaseVectorStoreService
) -> None:
    text_splitter = CustomTextSplitter()

    process = await update_progress_repository.get_update_process(vault_id)
    stage_id = await update_progress_repository.start_progress_stage(name="1. Vectorization", process_id=process["id"])
    
    if not files_to_update:
        logger.info("No files to update, finishing stage")
        await update_progress_repository.finish_progress_stage(stage_id=stage_id)
        return
    
    total_files = len(files_to_update)
    for idx, file_path in enumerate(files_to_update):
        filename = os.path.basename(file_path)
        try:
            if os.path.exists(file_path):
                # Remove old data and add updated data
                await vector_store.remove_chunks_of_file(vault_id, filename)
                async with aiofiles.open(file_path, encoding="utf-8") as f:
                    content = await f.read()
                text_chunks = text_splitter.split(filename[:-3] + " " + content)
                if text_chunks:
                    await vector_store.add_chunks(vault_id, text_chunks, [filename] * len(text_chunks))
                logger.info(f"Document {filename} has been updated successfully")
            else:
                # Remove document if it no longer exists
                await vector_store.remove_chunks_of_file(vault_id, filename)
                logger.info(f"Document {filename} has been removed successfully")
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}", exc_info=True)
            raise
        
        # Update progress after processing file (use idx + 1 to show actual progress)
        progress = int((idx + 1) * 100 / total_files)
        await update_progress_repository.update_progress_stage(
            stage_id=stage_id,
            progress=progress,
        )
        logger.info(f"Progress: {progress}% ({idx + 1}/{total_files})")

    await update_progress_repository.finish_progress_stage(stage_id=stage_id)
