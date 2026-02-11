import json
import logging

import aiohttp

from src.services.llm_service.base import BaseLLMService, LLMError

SUCCESS_HTTP_STATUS = 200

logger = logging.getLogger(__name__)


class OllamaLLMService(BaseLLMService):
    def __init__(self, model: str, base_url: str, max_tokens: int, token: str = "") -> None:  # noqa: ARG002
        self.model = model
        self.base_url = base_url.rstrip("/") if base_url else "http://localhost:11434"
        self.max_tokens = max_tokens
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_url = f"{self.base_url}/api/chat"

    async def _run_with_params(self, query: str, max_tokens: int) -> str:
        async with aiohttp.ClientSession() as client:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "options": {
                    "num_predict": max_tokens
                },
                "stream": False
            }
            headers = {
                "Content-Type": "application/json",
            }
            try:
                async with client.post(self.api_url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=600)) as resp:
                    logger.info(f"Ollama response status code: {resp.status}")
                    result = await resp.content.read()
                    logger.info(f"Ollama response content: {result}")
                    if resp.status != SUCCESS_HTTP_STATUS:
                        try:
                            error_dict = json.loads(result)
                            error_value = error_dict.get("error")
                            if isinstance(error_value, dict):
                                error_message = error_value.get("message", str(error_value))
                            elif isinstance(error_value, str):
                                error_message = error_value
                            else:
                                error_message = result.decode("utf-8")
                            raise LLMError(error_message)
                        except (json.decoder.JSONDecodeError, AttributeError, TypeError) as ex:
                            raise LLMError(result.decode("utf-8")) from ex
                    
                    result_dict = json.loads(result)
                    
                    # Ollama не всегда возвращает usage, поэтому используем приблизительные значения
                    if "usage" in result_dict:
                        self.input_tokens += result_dict["usage"].get("prompt_tokens", 0)
                        self.output_tokens += result_dict["usage"].get("completion_tokens", 0)
                    else:
                        # Приблизительный подсчет токенов (1 токен ≈ 4 символа)
                        self.input_tokens += len(query) // 4
                        self.output_tokens += len(result_dict.get("message", {}).get("content", "")) // 4
                    
                    return result_dict["message"]["content"]
            except aiohttp.ClientError as ex:
                raise LLMError(f"Connection error: {str(ex)}") from ex

    async def run(self, query: str) -> str:
        return await self._run_with_params(query, self.max_tokens)

    async def check(self) -> tuple[bool, str]:
        try:
            await self._run_with_params("test", 1)
        except LLMError as ex:
            return False, ex.message
        except Exception as ex:
            return False, f"Unexpected error: {str(ex)}"
        else:
            return True, ""

    async def get_used_tokens(self) -> tuple[int, int]:
        return self.input_tokens, self.output_tokens

