"""
Caché Redis para respuestas RAG.

Estrategia:
- Clave: SHA256 de la consulta normalizada (minúsculas, sin espacios extra)
- TTL: 48h — el contenido del RAG no cambia frecuentemente
- Solo se cachean respuestas del flujo RAG normal (no exámenes, no respuestas de estado)
- Si Redis no está disponible, el sistema sigue funcionando sin caché (fail-open)

Workers de uvicorn comparten el caché automáticamente a través de Redis.
"""

import hashlib
import json
import logging
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# TTL en segundos: 48 horas
CACHE_TTL = 48 * 3600

# Prefijo de claves en Redis
KEY_PREFIX = "bohr:rag:"

_redis_client = None
_redis_available = False


def _get_client():
    """Obtener cliente Redis, inicializando si es necesario."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client if _redis_available else None
    try:
        import redis
        client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True, socket_timeout=1)
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("✅ Caché Redis conectado")
    except Exception as e:
        _redis_client = None
        _redis_available = False
        logger.warning(f"⚠️  Redis no disponible — caché desactivado: {e}")
    return _redis_client if _redis_available else None


def _normalize(query: str) -> str:
    """Normalizar consulta para maximizar hits de caché."""
    q = query.lower().strip()
    q = re.sub(r"\s+", " ", q)           # espacios múltiples → uno
    q = re.sub(r"[¿?¡!.,;:]", "", q)     # quitar puntuación
    return q


def _make_key(query: str) -> str:
    digest = hashlib.sha256(_normalize(query).encode()).hexdigest()
    return f"{KEY_PREFIX}{digest}"


def get_cached(query: str) -> Optional[Dict[str, Any]]:
    """
    Buscar respuesta en caché.
    Retorna el dict cacheado, o None si no hay hit (o Redis no disponible).
    """
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(_make_key(query))
        if raw:
            logger.info(f"🎯 Cache HIT: '{query[:60]}'")
            return json.loads(raw)
    except Exception as e:
        logger.warning(f"Cache get error: {e}")
    return None


def set_cached(query: str, result: Dict[str, Any]) -> bool:
    """
    Guardar respuesta en caché con TTL de 48h.
    Retorna True si se guardó correctamente.
    """
    client = _get_client()
    if client is None:
        return False
    try:
        # No cachear mensajes de error ni respuestas muy cortas
        # synthesis_result usa "synthesized_answer"; respuestas finales usan "answer"
        answer = result.get("synthesized_answer", result.get("answer", ""))
        if len(answer) < 100:
            return False

        client.setex(_make_key(query), CACHE_TTL, json.dumps(result, ensure_ascii=False))
        logger.info(f"💾 Cache SET: '{query[:60]}' ({len(answer)} chars, TTL={CACHE_TTL//3600}h)")
        return True
    except Exception as e:
        logger.warning(f"Cache set error: {e}")
        return False


def invalidate_all() -> int:
    """
    Eliminar todas las entradas de caché de BOHR.
    Retorna el número de claves eliminadas.
    """
    client = _get_client()
    if client is None:
        return 0
    try:
        keys = client.keys(f"{KEY_PREFIX}*")
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache invalidate error: {e}")
        return 0


def get_stats() -> Dict[str, Any]:
    """Estadísticas del caché para el endpoint /health."""
    client = _get_client()
    if client is None:
        return {"available": False}
    try:
        info = client.info("stats")
        keys = len(client.keys(f"{KEY_PREFIX}*"))
        return {
            "available": True,
            "entries": keys,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
