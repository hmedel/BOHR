from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDINGS_MODEL: str = "nomic-embed-text"
    LLM_MODEL: str = "deepseek-chat"
    DEEPSEEK_API_KEY: str  # Required — set in .env, never hardcode
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    CHROMA_PATH: str = "./data/chroma"
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 300
    JWT_SECRET_KEY: Optional[str] = None  # Add JWT secret key field
    
    # Parámetros del LLM - BALANCE ENTRE PRECISIÓN Y ELABORACIÓN
    LLM_TEMPERATURE: float = 0.4  # Balance óptimo: elaboración moderada sin verbosidad
    LLM_MAX_TOKENS: int = 4000  # Suficiente para ecuaciones completas + explicación
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env

settings = Settings()
