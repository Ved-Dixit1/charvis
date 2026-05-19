import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./charvis.db"

    # Hugging Face
    HF_TOKEN: Optional[str] = None
    LOCAL_CACHE_DIR: Optional[str] = None

    # LLM Provider for generation
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # App server configurations
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Environment file config
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def hf_cache_path(self) -> str:
        if self.LOCAL_CACHE_DIR:
            return self.LOCAL_CACHE_DIR
        return str(Path.home() / ".cache" / "huggingface")

settings = Settings()
