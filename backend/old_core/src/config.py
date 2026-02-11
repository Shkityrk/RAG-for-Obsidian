from enum import Enum
from typing import Optional

from pydantic import DirectoryPath, Field, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationMode(Enum):
    DEBUG = "debug"
    PRODUCTION = "production"
    TEST = "test"


class ApplicationConfig(BaseSettings):
    OBSIDIAN_PATH: str = DirectoryPath()
    MODE: ApplicationMode = Field(default=ApplicationMode.DEBUG)
    DB_HOST: str = Field()
    DB_PORT: int = Field()
    DB_USER: str = Field()
    DB_PASSWORD: str = Field()
    DB_NAME: str = Field()
    ORIGINS: str = Field(default="")
    STATIC_PATH: Optional[str] = Field(default=None)
    QDRANT_URL: Optional[str] = Field(default=None)
    # Ollama settings
    OLLAMA_BASE_URL: str = Field(default="http://host.docker.internal:11434")
    LLM_MODEL: str = Field()
    EMBEDDING_MODEL: str = Field(default="mxbai-embed-large")
    LLM_MAX_TOKENS: int = Field(default=128000)
    # RAG settings
    SIMILARITY_THRESHOLD: float = Field(default=0.75, description="Минимальная косинусная похожесть для релевантных чанков (0.0-1.0)")
    MIN_RELEVANT_CHUNKS: int = Field(default=1, description="Минимальное количество релевантных чанков для генерации ответа")
    # Auth settings
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7, description="Access token expiration in minutes (7 days)")
    # Vault settings
    VAULTS_BASE_PATH: str = Field(default="/app/vaults", description="Base path for storing user vaults")
    # Yandex Search API settings
    YANDEX_AUTH_TOKEN: Optional[str] = Field(default=None, description="Yandex Search API auth token (Bearer token)")
    YANDEX_FOLDER_ID: Optional[str] = Field(default=None, description="Yandex Cloud folder ID")

    @property
    def is_debug(self) -> bool:
        return self.MODE == ApplicationMode.DEBUG

    @property
    def sync_db_url(self) -> str:
        return f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def async_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def origins(self) -> list[str]:
        return [origin for origin in self.ORIGINS.split(",") if origin != ""]

    model_config = SettingsConfigDict(env_file=".env")


app_config = ApplicationConfig()
