from pydantic_settings import BaseSettings
from pydantic import validator
from typing import Optional
import os

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Security - NO DEFAULTS for sensitive data!
    DEEPSEEK_API_KEY: str  # Required from environment
    JWT_SECRET: str  # Required from environment
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDINGS_MODEL: str = "nomic-embed-text:latest"
    
    # LLM Provider
    LLM_PROVIDER: str = "deepseek"
    
    # DeepSeek Configuration
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    LLM_MAX_TOKENS: int = 2000
    LLM_TEMPERATURE: float = 0.7
    
    # ChromaDB
    CHROMA_PATH: str = "./data/chroma"
    
    # RAG
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    BATCH_SIZE: int = 50  # Configurable batch size
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = 'utf-8'
    
    @validator('DEEPSEEK_API_KEY')
    def validate_api_key(cls, v):
        if not v or v.startswith("sk-CHANGE"):
            raise ValueError(
                "DeepSeek API key not configured. "
                "Please set DEEPSEEK_API_KEY in .env file"
            )
        return v
    
    @validator('JWT_SECRET')
    def validate_jwt_secret(cls, v):
        if not v or v == "CHANGE-ME-GENERATE-WITH-OPENSSL":
            raise ValueError(
                "JWT secret not configured. "
                "Generate one with: openssl rand -hex 32"
            )
        if len(v) < 32:
            raise ValueError("JWT secret too short. Use at least 32 characters")
        return v

settings = Settings()
