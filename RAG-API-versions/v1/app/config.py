from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDINGS_MODEL: str = "nomic-embed-text:latest"
    
    # LLM Provider
    LLM_PROVIDER: str = "deepseek"
    
    # DeepSeek Configuration
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_API_KEY: str  # Required — set in .env, never hardcode
    LLM_MODEL: str = "deepseek-chat"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.7
    
    # ChromaDB
    CHROMA_PATH: str = "./data/chroma"
    
    # RAG
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    
    class Config:
        env_file = ".env"
        case_sensitive = False  # Ignorar mayúsculas/minúsculas
        extra = "allow"  # Permitir campos extra

settings = Settings()
