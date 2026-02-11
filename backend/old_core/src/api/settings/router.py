from fastapi import APIRouter

# LLM settings endpoints removed - using hardcoded configuration from config.py
# Models are configured via environment variables:
# - OLLAMA_BASE_URL (default: http://host.docker.internal:11434)
# - LLM_MODEL (default: mistral-small3.2:latest)
# - EMBEDDING_MODEL (default: mxbai-embed-large)
# - LLM_MAX_TOKENS (default: 2048)

settings_router = APIRouter(prefix="/settings", tags=["settings"])
