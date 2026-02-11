from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException, status

from src.api.auth.dependencies import get_current_user
from src.api.general_dependencies import get_vector_store_service
from src.api.general_schemas import MessageResponse
from src.api.index.dependencies import get_file_repository, get_index_service_for_vault, get_update_progress_repository
from src.api.index.schemas import ClustersResponse, IndexInfoResponse, StageProgressSchema, UpdateIndexProgressResponse
from src.api.vaults.dependencies import get_vault_repository
from src.repositories.index.interface import FileRepository, UpdateProgressRepository
from src.repositories.vault.interface import VaultRepository
from src.services.index_service.base import BaseIndexService
from src.services.vector_store_service.base import BaseVectorStoreService
from src.utils.decomposition import get_decomposition_components
from src.utils.update_vector_store import update_vector_store

index_router = APIRouter(prefix="/index", tags=["index"])


@index_router.get("/info/", response_model=IndexInfoResponse)
async def get_index_info(
    vault_id: Annotated[int, Query(description="ID волта")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    file_repository: Annotated[FileRepository, Depends(get_file_repository)] = None,
    update_progress_repository: Annotated[UpdateProgressRepository, Depends(get_update_progress_repository)] = None,
) -> IndexInfoResponse:
    """Получить информацию об индексе волта"""
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Создаем IndexService для этого волта
    index_service = get_index_service_for_vault(
        vault_path=vault["path"],
        file_repository=file_repository,
        update_progress_repository=update_progress_repository
    )
    
    info = await index_service.get_info(vault_id)
    
    return IndexInfoResponse(
        n_documents_to_update=info["n_documents_to_update"],
        n_all_documents=info["n_all_documents"],
        last_update_time=info["last_update_time"],
        in_update_process=info["in_update_process"],
    )


@index_router.get("/clusters", response_model=ClustersResponse)
async def get_clusters(
    vault_id: Annotated[int, Query(description="ID волта")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    file_repository: Annotated[FileRepository, Depends(get_file_repository)] = None,
    update_progress_repository: Annotated[UpdateProgressRepository, Depends(get_update_progress_repository)] = None,
) -> ClustersResponse:
    """Получить кластеры файлов волта"""
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Создаем IndexService для этого волта
    index_service = get_index_service_for_vault(
        vault_path=vault["path"],
        file_repository=file_repository,
        update_progress_repository=update_progress_repository
    )
    
    clusters = await index_service.get_clusters(vault_id)
    return ClustersResponse.from_list(clusters)


@index_router.put("/", response_model=MessageResponse)
async def update_index(
    vault_id: Annotated[int, Query(description="ID волта")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    vector_store_service: Annotated[BaseVectorStoreService, Depends(get_vector_store_service)] = None,
    update_progress_repository: Annotated[UpdateProgressRepository, Depends(get_update_progress_repository)] = None,
    file_repository: Annotated[FileRepository, Depends(get_file_repository)] = None,
) -> MessageResponse:
    """Обновить индекс волта"""
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Создаем IndexService для этого волта
    index_service = get_index_service_for_vault(
        vault_path=vault["path"],
        file_repository=file_repository,
        update_progress_repository=update_progress_repository
    )
    
    # Проверяем, есть ли уже активный процесс обновления для этого волта
    current_process = await update_progress_repository.get_update_process(vault_id)
    if current_process:
        return MessageResponse(message="The index update operation has already started")

    process_id = await update_progress_repository.start_update_process(vault_id)
    try:
        # Обновляем статус волта
        await vault_repo.update_status(vault_id, "indexing")
        
        files_to_update = await index_service.find_files_to_update(vault_id)
        await update_vector_store(vault_id, files_to_update, update_progress_repository, vector_store_service)
        results = await get_decomposition_components(vault_id, files_to_update, file_repository, vector_store_service)
        await index_service.update(vault_id, results)
        await update_progress_repository.finish_update_process(process_id=process_id)
        
        # Обновляем статус волта
        await vault_repo.update_status(vault_id, "ready")
        
        return MessageResponse(message="Index has been updated")
    except Exception as e:
        # Обновляем статус волта на error
        await vault_repo.update_status(vault_id, "error")
        # Finish process even on error to prevent stuck state
        await update_progress_repository.finish_update_process(process_id=process_id)
        raise


@index_router.get("/progress", response_model=UpdateIndexProgressResponse)
async def get_index_progress(
    vault_id: Annotated[int, Query(description="ID волта")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    update_progress_repository: Annotated[UpdateProgressRepository, Depends(get_update_progress_repository)] = None,
) -> UpdateIndexProgressResponse:
    """Получить прогресс индексации волта"""
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    process = await update_progress_repository.get_update_process(vault_id)
    if not process:
        return UpdateIndexProgressResponse(in_progress=False, stages=[])
    stages = await update_progress_repository.get_stages_by_process(process["id"])
    return UpdateIndexProgressResponse(
        in_progress=True,
        stages=[
            StageProgressSchema(name=stage["name"], value=stage["progress"])
            for stage in stages
        ]
    )


@index_router.post("/reset-process/", response_model=MessageResponse)
async def reset_update_process(
    vault_id: Annotated[int, Query(description="ID волта")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    update_progress_repository: Annotated[UpdateProgressRepository, Depends(get_update_progress_repository)] = None,
) -> MessageResponse:
    """Сбросить застрявший процесс обновления индекса"""
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Finish all active processes to handle any stuck state
    count = await update_progress_repository.finish_all_active_processes(vault_id)
    if count == 0:
        return MessageResponse(message="No active update process found")
    
    # Обновляем статус волта
    await vault_repo.update_status(vault_id, "ready")
    
    return MessageResponse(message=f"Reset {count} update process(es)")


@index_router.delete("/", response_model=MessageResponse)
async def delete_index(
    vault_id: Annotated[int, Query(description="ID волта")],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    vault_repo: Annotated[VaultRepository, Depends(get_vault_repository)] = None,
    file_repository: Annotated[FileRepository, Depends(get_file_repository)] = None,
    update_progress_repository: Annotated[UpdateProgressRepository, Depends(get_update_progress_repository)] = None,
    vector_store_service: Annotated[BaseVectorStoreService, Depends(get_vector_store_service)] = None,
) -> MessageResponse:
    """Удалить индекс волта"""
    # Проверка прав доступа к волту
    vault = await vault_repo.get_by_id(vault_id)
    if not vault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault not found"
        )
    if vault["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Создаем IndexService для этого волта
    index_service = get_index_service_for_vault(
        vault_path=vault["path"],
        file_repository=file_repository,
        update_progress_repository=update_progress_repository
    )
    
    await vector_store_service.remove_all_chunks(vault_id)
    await index_service.remove(vault_id)
    return MessageResponse(message="Index deleted successfully")
