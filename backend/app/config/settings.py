from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # API settings
    API_V1_STR: str = "/api"
    
    # CORS settings
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # Claude API settings
    CLAUDE_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "your-api-key-here")
    CLAUDE_MODEL: str = os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")
    
    # LlamaCloud settings
    LLAMA_CLOUD_API_KEY: str = os.environ.get("LLAMA_CLOUD_API_KEY", "your-llama-cloud-api-key")
    LLAMA_CLOUD_INDEX_PREFIX: str = os.environ.get("LLAMA_CLOUD_INDEX_PREFIX", "agent-builder")
    LLAMA_CLOUD_PROJECT_NAME: str = os.environ.get("LLAMA_CLOUD_PROJECT_NAME", "Default")
    
    # Knowledge base settings
    # KNOWLEDGE_RELEVANCE_THRESHOLD - Range from 0.0 to 1.0, higher values mean stricter matching
    # - Lower values (e.g., 0.5): More documents will be considered relevant, possibly including less precise matches
    # - Higher values (e.g., 0.8): Only very closely matching documents will be included
    # Recommended range: 0.6 - 0.8 depending on your knowledge base quality
    KNOWLEDGE_RELEVANCE_THRESHOLD: float = float(os.getenv("KNOWLEDGE_RELEVANCE_THRESHOLD", "0.7"))
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    
    # Logging settings
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings():
    """
    Get cached settings instance.
    Using lru_cache to avoid re-reading .env file on every request.
    """
    return Settings()


# Create settings instance
settings = get_settings()