from pydantic_settings import BaseSettings
from typing import Optional

# ── Versiones del sistema para trazabilidad (P1.2) ──────────────────────────
# Actualizar cuando cambie la lógica de clasificación o el modelo LLM.
# Estas constantes se graban en messages.classifier_meta para que cada
# clasificación pueda asociarse a la versión exacta del sistema.
#
# classifier_version: incrementar cuando cambie BLOOM_KEYWORDS o la lógica
#   de classify_bloom_level (usar semver, e.g. "1.1.0" → "1.2.0")
# model_version: nombre del modelo LLM y su versión visible de la API
# prompt_version: incrementar cuando cambie el prompt de síntesis RAG
#
# Historial:
#   v1.0.0 (2026-04): substring match, default="comprender"
#   v1.1.0 (2026-08): word-boundary (\b), default="no_clasificado" [actual]
CLASSIFIER_VERSION = "1.1.0"
MODEL_VERSION = "deepseek-chat-v3"   # Nombre del modelo en la API de DeepSeek
PROMPT_VERSION = "2.8"               # Coincide con app version; incrementar con cada cambio de prompt

class Settings(BaseSettings):
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDINGS_MODEL: str = "nomic-embed-text"
    LLM_MODEL: str = "deepseek-chat"
    DEEPSEEK_API_KEY: str  # Required — set in .env, never hardcode
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    CHROMA_PATH: str = "./data/chroma"
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 300
    JWT_SECRET_KEY: str  # Required — set in .env, never hardcode
    
    # Parámetros del LLM - BALANCE ENTRE PRECISIÓN Y ELABORACIÓN
    LLM_TEMPERATURE: float = 0.4  # Balance óptimo: elaboración moderada sin verbosidad
    LLM_MAX_TOKENS: int = 2500  # Suficiente para respuestas completas; bajar de 4000 reduce latencia ~20-30%
    CHUNKS_PER_SOURCE: int = 7  # Chunks por fuente (bajado de 10); mantiene calidad, reduce contexto ~30%
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env

settings = Settings()
