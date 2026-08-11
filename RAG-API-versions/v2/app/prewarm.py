"""
Pre-warming del caché Redis para BOHR RAG v2.

Ejecuta las preguntas canónicas del temario de Estructura de la Materia
contra el pipeline RAG completo y guarda las respuestas en Valkey.

Uso:
    python -m app.prewarm                  # calentar todo
    python -m app.prewarm --dry-run        # solo mostrar preguntas, no ejecutar
    python -m app.prewarm --topic orbitales  # solo un tópico

Se puede llamar también al arranque del backend (ver main.py startup event).
Las preguntas ya en caché se saltan automáticamente (no se vuelven a generar).
"""

import asyncio
import argparse
import time
import sys
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("prewarm")

# ============================================================
# PREGUNTAS CANÓNICAS DEL TEMARIO
# Basadas en consultas reales de la DB y el programa de la materia.
# Una por concepto — la forma más directa y común.
# ============================================================

CANONICAL_QUESTIONS: List[Dict] = [

    # ── ESTRUCTURA ATÓMICA ──────────────────────────────────
    {"topic": "estructura_atomica", "q": "¿Qué es el átomo y cuál es su estructura?"},
    {"topic": "estructura_atomica", "q": "¿Qué es la carga nuclear efectiva?"},
    {"topic": "estructura_atomica", "q": "¿Qué es la energía de ionización?"},
    {"topic": "estructura_atomica", "q": "¿Qué es el radio atómico y cómo varía en la tabla periódica?"},
    {"topic": "estructura_atomica", "q": "¿Qué es el radio de Van der Waals?"},
    {"topic": "estructura_atomica", "q": "¿Cuántos electrones caben en las capas K, L, M y N?"},
    {"topic": "estructura_atomica", "q": "¿Cuál es la diferencia entre electrones de valencia y electrones de capa interna?"},
    {"topic": "estructura_atomica", "q": "¿Cómo cambian las propiedades a lo largo de los períodos y familias de la tabla periódica?"},
    {"topic": "estructura_atomica", "q": "¿A qué se deben las anomalías en las configuraciones electrónicas?"},

    # ── MECÁNICA CUÁNTICA ───────────────────────────────────
    {"topic": "mecanica_cuantica", "q": "¿Cuál es la ecuación de Schrödinger independiente del tiempo y qué significa cada término?"},
    {"topic": "mecanica_cuantica", "q": "¿Qué es el principio de incertidumbre de Heisenberg?"},
    {"topic": "mecanica_cuantica", "q": "¿Qué es la dualidad onda-partícula?"},
    {"topic": "mecanica_cuantica", "q": "¿Qué es la función de onda y qué representa físicamente?"},
    {"topic": "mecanica_cuantica", "q": "¿Qué es el principio de exclusión de Pauli?"},
    {"topic": "mecanica_cuantica", "q": "¿Qué es la ecuación de Dirac y para qué sirve?"},
    {"topic": "mecanica_cuantica", "q": "¿Cuál es el modelo cuántico del átomo de hidrógeno?"},
    {"topic": "mecanica_cuantica", "q": "¿Qué es el operador hamiltoniano?"},

    # ── ORBITALES Y NÚMEROS CUÁNTICOS ──────────────────────
    {"topic": "orbitales", "q": "¿Qué es el número cuántico de espín?"},
    {"topic": "orbitales", "q": "¿Cuáles son los cuatro números cuánticos y qué describe cada uno?"},
    {"topic": "orbitales", "q": "¿Qué forma tienen los orbitales s, p, d y f?"},
    {"topic": "orbitales", "q": "¿Qué es la hibridación de orbitales?"},
    {"topic": "orbitales", "q": "¿Qué es la regla de Hund?"},
    {"topic": "orbitales", "q": "¿Qué es el principio de Aufbau?"},
    {"topic": "orbitales", "q": "¿Cómo se escribe la configuración electrónica de un elemento?"},
    {"topic": "orbitales", "q": "¿Qué es un orbital molecular y cómo se forma?"},

    # ── ESPECTROSCOPIA ──────────────────────────────────────
    {"topic": "espectroscopia", "q": "¿Qué es el espectro de emisión del hidrógeno?"},
    {"topic": "espectroscopia", "q": "¿Qué es la serie de Balmer?"},
    {"topic": "espectroscopia", "q": "¿Qué es la constante de Rydberg?"},
    {"topic": "espectroscopia", "q": "¿Cómo se relaciona la energía de un fotón con su frecuencia?"},
    {"topic": "espectroscopia", "q": "¿Qué es el efecto fotoeléctrico?"},

    # ── ENLACES QUÍMICOS ────────────────────────────────────
    {"topic": "enlaces_quimicos", "q": "¿Qué es un enlace covalente y cómo se forma?"},
    {"topic": "enlaces_quimicos", "q": "¿Qué es un enlace iónico?"},
    {"topic": "enlaces_quimicos", "q": "¿Qué es la electronegatividad y cómo varía en la tabla periódica?"},
    {"topic": "enlaces_quimicos", "q": "¿Qué es la energía de disociación de un enlace?"},

    # ── ESTRUCTURA MOLECULAR ────────────────────────────────
    {"topic": "estructura_molecular", "q": "¿Qué es la teoría VSEPR y cómo se usa para predecir geometrías?"},
    {"topic": "estructura_molecular", "q": "¿Qué es el momento dipolar de una molécula?"},
    {"topic": "estructura_molecular", "q": "¿Cuál es la geometría molecular del agua y del metano?"},
]


async def warm_single(question: str, rag_engine, cache_module) -> Dict:
    """Calentar una pregunta individual. Retorna resultado con métricas."""
    # Verificar si ya está en caché
    cached = cache_module.get_cached(question)
    if cached:
        return {"question": question, "status": "skip", "time": 0}

    t0 = time.time()
    try:
        result = await rag_engine.query_multi_source_with_synthesis(
            query=question,
            sources_count=3,
        )
        elapsed = time.time() - t0

        if result.get("synthesized_answer"):
            cache_module.set_cached(question, result)
            return {"question": question, "status": "ok", "time": elapsed,
                    "chars": len(result["synthesized_answer"]),
                    "sources": result.get("sources_used", [])}
        else:
            return {"question": question, "status": "empty", "time": elapsed}

    except Exception as e:
        return {"question": question, "status": "error", "time": time.time() - t0, "error": str(e)}


async def run_prewarm(questions: List[Dict], dry_run: bool = False):
    """Ejecutar pre-warming sobre la lista de preguntas."""
    if dry_run:
        logger.info(f"DRY RUN — {len(questions)} preguntas (no se ejecutará nada):")
        for i, item in enumerate(questions, 1):
            logger.info(f"  {i:2}. [{item['topic']}] {item['q']}")
        return

    # Importar dentro del contexto correcto de la app
    from app.rag_engine import RAGEngine
    from app import cache as rag_cache

    logger.info(f"🔥 Iniciando pre-warming: {len(questions)} preguntas canónicas")
    rag = RAGEngine()

    stats = {"ok": 0, "skip": 0, "error": 0, "empty": 0}
    total_time = 0

    for i, item in enumerate(questions, 1):
        q = item["q"]
        topic = item["topic"]
        logger.info(f"[{i:2}/{len(questions)}] {topic} — {q[:60]}...")

        result = await warm_single(q, rag, rag_cache)
        stats[result["status"]] += 1
        total_time += result["time"]

        if result["status"] == "ok":
            logger.info(f"  ✅ {result['time']:.1f}s — {result['chars']} chars, {len(result['sources'])} fuentes")
        elif result["status"] == "skip":
            logger.info(f"  ⏭️  Ya en caché, saltando")
        elif result["status"] == "error":
            logger.warning(f"  ❌ Error: {result.get('error', '')[:80]}")
        elif result["status"] == "empty":
            logger.warning(f"  ⚠️  Respuesta vacía")

        # Pausa entre consultas para no saturar DeepSeek
        if result["status"] == "ok" and i < len(questions):
            await asyncio.sleep(2)

    logger.info("")
    logger.info("═" * 50)
    logger.info(f"Pre-warming completado:")
    logger.info(f"  ✅ Generadas: {stats['ok']}")
    logger.info(f"  ⏭️  Saltadas (ya en caché): {stats['skip']}")
    logger.info(f"  ❌ Errores: {stats['error']}")
    logger.info(f"  ⚠️  Vacías: {stats['empty']}")
    logger.info(f"  ⏱  Tiempo total: {total_time:.0f}s ({total_time/60:.1f} min)")
    logger.info("═" * 50)


def main():
    parser = argparse.ArgumentParser(description="Pre-warming del caché RAG de BOHR")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar preguntas sin ejecutar")
    parser.add_argument("--topic", type=str, default=None,
                        help="Filtrar por tópico (ej: orbitales, mecanica_cuantica)")
    args = parser.parse_args()

    questions = CANONICAL_QUESTIONS
    if args.topic:
        questions = [q for q in questions if q["topic"] == args.topic]
        if not questions:
            print(f"Tópico '{args.topic}' no encontrado. Disponibles: "
                  f"{list(set(q['topic'] for q in CANONICAL_QUESTIONS))}")
            sys.exit(1)

    asyncio.run(run_prewarm(questions, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
