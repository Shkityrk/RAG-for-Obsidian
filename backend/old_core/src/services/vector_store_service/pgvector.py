import asyncio
import logging

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from src.config import app_config
from src.database.models import ChunkEmbeddingModel
from src.services.embeddings_service.base import BaseEmbeddingsService, EmbeddingsError
from src.services.vector_store_service.base import BaseVectorStoreService

logger = logging.getLogger(__name__)


class PGVectorStoreService(BaseVectorStoreService):
    def __init__(self, session: AsyncSession, embedding_service: BaseEmbeddingsService) -> None:
        self.session = session
        self.embedding_service = embedding_service

    async def retrieve(self, query: str, k: int, vault_id: int, similarity_threshold: float | None = None) -> list[dict]:
        """
        Извлекает релевантные чанки с фильтрацией по similarity threshold.
        
        Args:
            query: Текст запроса
            k: Максимальное количество чанков для извлечения после фильтрации
            vault_id: ID волта для фильтрации чанков
            similarity_threshold: Минимальная косинусная похожесть (если None, используется из config)
        
        Returns:
            Список чанков с дополнительным полем 'similarity' (косинусная похожесть)
        """
        embed = await self.embedding_service.embed_one(query)
        threshold = similarity_threshold if similarity_threshold is not None else app_config.SIMILARITY_THRESHOLD
        
        # Получаем больше кандидатов (k*3) для последующей фильтрации по threshold
        # Это нужно, так как фильтрация по similarity происходит в Python
        candidate_limit = max(k * 3, 20)
        
        # Получаем кандидатов, отсортированных по косинусному расстоянию, фильтруем по vault_id
        statement = (
            select(ChunkEmbeddingModel)
            .where(ChunkEmbeddingModel.vault_id == vault_id)
            .order_by(ChunkEmbeddingModel.embedding.cosine_distance(embed))
            .limit(candidate_limit)
        )
        
        results = await self.session.execute(statement)
        chunks = results.scalars().all()
        
        if not chunks:
            logger.info(f"No chunks found in database for query: {query[:50]}...")
            return []
        
        # Вычисляем similarity для каждого чанка в Python используя numpy
        # Преобразуем query embedding в numpy array
        query_vec = np.array(embed, dtype=np.float32)
        
        filtered_chunks = []
        for chunk in chunks:
            # Получаем embedding чанка и преобразуем в numpy array
            chunk_vec = np.array(chunk.embedding, dtype=np.float32)
            
            # Вычисляем косинусную похожесть: dot product / (norm1 * norm2)
            dot_product = np.dot(query_vec, chunk_vec)
            norm_query = np.linalg.norm(query_vec)
            norm_chunk = np.linalg.norm(chunk_vec)
            
            if norm_query == 0 or norm_chunk == 0:
                similarity = 0.0
            else:
                similarity = float(dot_product / (norm_query * norm_chunk))
            
            # Фильтруем по threshold
            if similarity >= threshold:
                chunk_dict = chunk.model_dump()
                chunk_dict['similarity'] = similarity
                filtered_chunks.append(chunk_dict)
                
                # Останавливаемся, если нашли достаточно чанков
                if len(filtered_chunks) >= k:
                    break
        
        if not filtered_chunks:
            logger.info(
                f"No chunks found above similarity threshold {threshold} for query: {query[:50]}... "
                f"(checked {len(chunks)} candidates)"
            )
            return []
        
        # Сортируем по similarity (от большего к меньшему)
        filtered_chunks.sort(key=lambda x: x['similarity'], reverse=True)
        
        logger.info(
            f"Retrieved {len(filtered_chunks)} chunks above threshold {threshold} "
            f"(similarity range: {filtered_chunks[-1]['similarity']:.3f} - {filtered_chunks[0]['similarity']:.3f}, "
            f"checked {len(chunks)} candidates)"
        )
        
        return filtered_chunks

    async def add_chunks(self, vault_id: int, texts: list[str], filenames: list[str]) -> None:
        try:
            embeds = await self.embedding_service.embed_many(texts)
        except EmbeddingsError:
            await asyncio.sleep(2)
            embeds = await self.embedding_service.embed_many(texts)
        for embed, text, filename in zip(embeds, texts, filenames):
            chunk_embedding = ChunkEmbeddingModel(
                vault_id=vault_id,
                filename=filename,
                text=text,
                embedding=embed
            )
            self.session.add(chunk_embedding)
        await self.session.commit()

    async def remove_chunks_of_file(self, vault_id: int, filename: str) -> None:
        statement = (
            delete(ChunkEmbeddingModel)
            .where(
                ChunkEmbeddingModel.vault_id == vault_id,
                ChunkEmbeddingModel.filename == filename
            )
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def remove_all_chunks(self, vault_id: int) -> None:
        statement = delete(ChunkEmbeddingModel).where(ChunkEmbeddingModel.vault_id == vault_id)
        await self.session.execute(statement)
        await self.session.commit()

    async def get_chunks_of_file(self, vault_id: int, filename: str) -> list[dict]:
        statement = (
            select(ChunkEmbeddingModel)
            .where(
                ChunkEmbeddingModel.vault_id == vault_id,
                ChunkEmbeddingModel.filename == filename
            )
        )
        results = await self.session.execute(statement)
        files = results.scalars().all()
        return [file.model_dump() for file in files]
