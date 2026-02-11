import asyncio
import logging
import re

from src.config import app_config
from src.services.llm_service.base import BaseLLMService, LLMError
from src.services.rag_service.base import BaseRagService, RagResponse, FragmentInfo
from src.services.vector_store_service.base import BaseVectorStoreService
from src.utils.yandex_search_api import main as yandex_search_main, get_yandex_search_results, preprocess_text

logger = logging.getLogger(__name__)


# Промпт для случая, когда есть релевантный контекст
PROMPT_WITH_CONTEXT = """\
Context information from Obsidian notes is below. ONLY use it if DIRECTLY relevant to the query.
If the context is unrelated or empty, respond EXACTLY as specified in the fallback instructions.
---------------------
%s
---------------------
Query: %s

Instructions:
- Answer ONLY from the provided context if it directly relates to the query
- If context is unrelated or empty, use the fallback response below
- Do NOT make up information or use prior knowledge beyond the context

Answer:"""

# Промпт для случая, когда нет релевантного контекста
PROMPT_NO_CONTEXT = """\
Query: %s

Instructions:
- The question is not directly related to topics in my Obsidian notes
- Respond EXACTLY in this format:
  "Извините, в моих Obsidian-заметках нет информации по этой теме"""


class FinalRagService(BaseRagService):
    def __init__(self, llm: BaseLLMService, vector_store: BaseVectorStoreService) -> None:
        self.llm = llm
        self.vector_store = vector_store

    async def run(self, user_query: str, vault_id: int) -> RagResponse:
        # Извлекаем релевантные фрагменты с фильтрацией по threshold
        fragments = await self.vector_store.retrieve(user_query, k=5, vault_id=vault_id)
        
        # Проверяем, есть ли достаточно релевантных чанков
        min_chunks = app_config.MIN_RELEVANT_CHUNKS
        has_relevant_context = len(fragments) >= min_chunks
        
        # Проверяем максимальную косинусную похожесть среди найденных фрагментов
        max_similarity = max([fragment.get("similarity", 0.0) for fragment in fragments]) if fragments else 0.0
        similarity_threshold = app_config.SIMILARITY_THRESHOLD
        
        # Если нет релевантного контекста или низкая косинусная похожесть, используем Yandex поиск
        if not has_relevant_context or max_similarity < similarity_threshold:
            logger.warning(
                f"Not enough relevant chunks found ({len(fragments)} < {min_chunks}) "
                f"or low similarity ({max_similarity:.3f} < {similarity_threshold}). "
                f"Using Yandex search for query: {user_query[:50]}..."
            )
            
            # Проверяем, настроены ли креды Yandex
            if app_config.YANDEX_AUTH_TOKEN and app_config.YANDEX_FOLDER_ID:
                try:
                    # Используем поиск через Yandex API
                    answer = await yandex_search_main(user_query)
                    used_tokens = await self.llm.get_used_tokens()
                    
                    return RagResponse(
                        answer=answer,
                        related_documents=[],
                        used_tokens=used_tokens,
                        fragments=[]
                    )
                except Exception as e:
                    logger.error(f"Ошибка при использовании Yandex поиска: {e}", exc_info=True)
                    # Продолжаем с обычным fallback промптом
            else:
                logger.warning("Yandex credentials not configured, using fallback prompt")
            
            # Используем промпт без контекста как fallback
            prompt = PROMPT_NO_CONTEXT % user_query
            related_documents = []
            fragment_infos = []
        else:
            # Есть релевантный контекст
            related_documents = {fragment["filename"] for fragment in fragments}
            logger.info(
                f"Retrieved {len(fragments)} relevant fragments from {len(related_documents)} documents. "
                f"Similarity scores: {[f.get('similarity', 'N/A') for f in fragments[:3]]}"
            )
            retrieved_context = "\n\n".join([fragment["text"] for fragment in fragments])
            prompt = PROMPT_WITH_CONTEXT % (retrieved_context, user_query)
            
            # Преобразуем фрагменты в FragmentInfo
            fragment_infos = [
                FragmentInfo(
                    filename=fragment["filename"],
                    text=fragment["text"],
                    similarity=fragment.get("similarity", 0.0),
                    chunk_id=fragment.get("id")
                )
                for fragment in fragments
            ]
        
        try:
            answer = await self.llm.run(prompt)
        except LLMError as ex:
            logger.warning(f"LLM error: {ex!s}, retrying...")
            await asyncio.sleep(2)
            answer = await self.llm.run(prompt)
        
        
        
        used_tokens = await self.llm.get_used_tokens()
        
        logger.info(f"Returning RagResponse with {len(fragment_infos)} fragments")
        if fragment_infos:
            logger.info(f"First fragment info: filename={fragment_infos[0].filename}, similarity={fragment_infos[0].similarity}")
        
        return RagResponse(
            answer=answer, 
            related_documents=list(related_documents), 
            used_tokens=used_tokens,
            fragments=fragment_infos
        )
    
    async def run_combined_search(self, user_query: str, vault_id: int) -> RagResponse:
        """
        Выполняет комбинированный поиск: сначала в Obsidian vault, затем в Yandex.
        Объединяет результаты с приоритетом Obsidian.
        
        Args:
            user_query: Запрос пользователя
            vault_id: ID vault для поиска в Obsidian
            
        Returns:
            RagResponse с объединенным ответом
        """
        logger.info(f"Запуск комбинированного поиска для запроса: {user_query[:50]}...")
        
        # Шаг 1: Поиск в Obsidian vault
        logger.info("Шаг 1: Поиск в Obsidian vault...")
        obsidian_fragments = await self.vector_store.retrieve(user_query, k=5, vault_id=vault_id)
        
        # Шаг 2: Поиск в Yandex (если настроены креды)
        yandex_results = None
        yandex_generative = None
        if app_config.YANDEX_AUTH_TOKEN and app_config.YANDEX_FOLDER_ID:
            try:
                logger.info("Шаг 2: Поиск в Yandex...")
                yandex_results, yandex_generative = await get_yandex_search_results(user_query)
                logger.info(f"Получены результаты Yandex: {len(yandex_results)} символов")
            except Exception as e:
                logger.error(f"Ошибка при поиске в Yandex: {e}", exc_info=True)
                yandex_results = None
                yandex_generative = None
        
        # Шаг 3: Формируем контекст с приоритетом Obsidian
        context_parts = []
        
        # Сначала добавляем результаты из Obsidian (приоритет)
        if obsidian_fragments:
            obsidian_context = "\n\n".join([fragment["text"] for fragment in obsidian_fragments])
            context_parts.append(f"=== ИНФОРМАЦИЯ ИЗ OBSIDIAN VAULT (ПРИОРИТЕТ) ===\n{obsidian_context}")
            logger.info(f"Добавлено {len(obsidian_fragments)} фрагментов из Obsidian")
        
        # Затем добавляем результаты из Yandex (дополнительная информация)
        if yandex_results or yandex_generative:
            yandex_context_parts = []
            if yandex_results:
                preprocessed_yandex = preprocess_text(yandex_results)
                yandex_context_parts.append(f"РЕЗУЛЬТАТЫ ПОИСКА В ИНТЕРНЕТЕ:\n{preprocessed_yandex}")
            if yandex_generative:
                preprocessed_generative = preprocess_text(yandex_generative)
                yandex_context_parts.append(f"\nГЕНЕРАТИВНЫЙ ОТВЕТ ОТ ЯНДЕКСА:\n{preprocessed_generative}")
            
            if yandex_context_parts:
                context_parts.append(f"\n=== ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ИЗ ИНТЕРНЕТА ===\n" + "\n".join(yandex_context_parts))
                logger.info("Добавлены результаты из Yandex")
        
        # Формируем промпт для LLM
        PROMPT_COMBINED = """СИСТЕМА: Ты помощник, который отвечает на вопросы на основе информации из Obsidian vault и дополнительной информации из интернета.

ИНСТРУКЦИЯ: 
- Информация из Obsidian vault имеет ПРИОРИТЕТ и должна быть основой ответа
- Дополнительная информация из интернета используется только для дополнения и уточнения
- Если информация из Obsidian противоречит информации из интернета, приоритет у Obsidian
- Ответ должен быть структурированным и полным

КОНТЕКСТ:
{context}

ВОПРОС: {user_query}

ОТВЕТ:"""
        
        context = "\n".join(context_parts) if context_parts else "Контекст не найден."
        prompt = PROMPT_COMBINED.format(context=context, user_query=user_query)
        
        # Шаг 4: Генерируем ответ через LLM
        logger.info("Шаг 3: Генерация ответа через LLM...")
        try:
            answer = await self.llm.run(prompt)
        except LLMError as ex:
            logger.warning(f"LLM error: {ex!s}, retrying...")
            await asyncio.sleep(2)
            answer = await self.llm.run(prompt)
        
        used_tokens = await self.llm.get_used_tokens()
        
        # Формируем FragmentInfo только из Obsidian фрагментов
        fragment_infos = [
            FragmentInfo(
                filename=fragment["filename"],
                text=fragment["text"],
                similarity=fragment.get("similarity", 0.0),
                chunk_id=fragment.get("id")
            )
            for fragment in obsidian_fragments
        ]
        
        related_documents = {fragment["filename"] for fragment in obsidian_fragments} if obsidian_fragments else set()
        
        logger.info(f"Комбинированный поиск завершен. Использовано {len(fragment_infos)} фрагментов из Obsidian.")
        
        return RagResponse(
            answer=answer,
            related_documents=list(related_documents),
            used_tokens=used_tokens,
            fragments=fragment_infos
        )
