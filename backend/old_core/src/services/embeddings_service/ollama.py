import asyncio
import json
import logging

import aiohttp

from src.services.embeddings_service.base import BaseEmbeddingsService, EmbeddingsError

SUCCESS_HTTP_STATUS = 200

# Максимальная длина чанка в символах для модели mxbai-embed-large
# Безопасное значение - примерно 256-300 символов (≈64-75 токенов)
MAX_CHUNK_LENGTH = 256 

logger = logging.getLogger(__name__)


class OllamaEmbeddingsService(BaseEmbeddingsService):
    def __init__(self, model: str, base_url: str = "", batch_size: int = 10) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "http://localhost:11434"
        self.batch_size = batch_size
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_url = f"{self.base_url}/api/embeddings"

    async def _run(self, query: str) -> list[float]:
        # Финальная проверка и обрезка на случай, если чанк все еще слишком большой
        if len(query) > MAX_CHUNK_LENGTH:
            logger.warning(f"Chunk still too long after splitting ({len(query)} chars), truncating to {MAX_CHUNK_LENGTH}")
            query = query[:MAX_CHUNK_LENGTH]
        
        async with aiohttp.ClientSession() as client:
            payload = {
                "model": self.model,
                "prompt": query,
            }
            headers = {
                "Content-Type": "application/json",
            }
            try:
                async with client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=600)
                ) as resp:
                    logger.info(f"Ollama embeddings response status code: {resp.status}")
                    result = await resp.content.read()
                    if resp.status != SUCCESS_HTTP_STATUS:
                        logger.warning(f"Ollama embeddings response content: {result}")
                        try:
                            error_dict = json.loads(result)
                            error_value = error_dict.get("error")
                            if isinstance(error_value, dict):
                                error_message = error_value.get("message", str(error_value))
                            elif isinstance(error_value, str):
                                error_message = error_value
                            else:
                                error_message = result.decode("utf-8")
                            raise EmbeddingsError(error_message)
                        except (json.decoder.JSONDecodeError, AttributeError, TypeError) as ex:
                            raise EmbeddingsError(result.decode("utf-8")) from ex
                    
                    result_dict = json.loads(result)
                    embedding = result_dict.get("embedding", [])
                    
                    # Приблизительный подсчет токенов (1 токен ≈ 4 символа)
                    self.input_tokens += len(query) // 4
                    self.output_tokens += len(str(embedding)) // 4
                    
                    return embedding
            except aiohttp.ClientError as ex:
                raise EmbeddingsError(f"Connection error: {str(ex)}") from ex

    async def embed_one(self, query: str) -> list[float]:
        return await self._run(query)

    async def embed_many(self, queries: list[str]) -> list[list[float]]:
        embeds = []
        for query in queries:
            # Разбиваем слишком большие чанки на безопасные размеры
            if len(query) > MAX_CHUNK_LENGTH:
                logger.warning(f"Chunk too long ({len(query)} chars), splitting into {MAX_CHUNK_LENGTH}-char pieces...")
                # Разбиваем на части по MAX_CHUNK_LENGTH, стараясь разбивать по словам/предложениям
                chunks = self._smart_split(query, MAX_CHUNK_LENGTH)
                for chunk in chunks:
                    if chunk.strip():  # Пропускаем пустые чанки
                        embed = await self._run(chunk)
                        embeds.append(embed)
                    await asyncio.sleep(0.05)  # Небольшая задержка между подчанками
            else:
                embed = await self._run(query)
                embeds.append(embed)
            await asyncio.sleep(0.1)
        return embeds

    def _smart_split(self, text: str, max_length: int) -> list[str]:
        """Разбивает текст на чанки, стараясь не разрывать слова и предложения."""
        chunks = []
        current_chunk = ""
        
        # Сначала пытаемся разбить по предложениям
        sentences = text.replace('. ', '.\n').replace('! ', '!\n').replace('? ', '?\n').split('\n')
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Если предложение само по себе больше max_length, разбиваем его принудительно
            if len(sentence) > max_length:
                # Сначала сохраняем текущий чанк, если он есть
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                # Разбиваем длинное предложение по словам
                words = sentence.split()
                for word in words:
                    if len(current_chunk) + len(word) + 1 <= max_length:
                        current_chunk += " " + word if current_chunk else word
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word
                        # Если слово само по себе больше max_length, обрезаем его
                        if len(current_chunk) > max_length:
                            chunks.append(current_chunk[:max_length])
                            current_chunk = current_chunk[max_length:]
            else:
                # Если добавление предложения не превысит лимит, добавляем
                if len(current_chunk) + len(sentence) + 1 <= max_length:
                    current_chunk += " " + sentence if current_chunk else sentence
                else:
                    # Сохраняем текущий чанк и начинаем новый
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
        
        # Добавляем последний чанк
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text[:max_length]]  # Fallback на простое разбиение

    async def get_used_tokens(self) -> tuple[int, int]:
        return self.input_tokens, self.output_tokens

