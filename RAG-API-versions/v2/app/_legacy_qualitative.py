"""
Codigo legado del evaluador cualitativo — NO importar en produccion.

Este modulo preserva las funciones que existian en qualitative_evaluator.py
antes de la auditoria pedagogica (agosto 2026). Se conserva para:

  1. Referencia historica del articulo PAPIME (datos de linea base).
  2. Documentar exactamente que media cada funcion y sus limitaciones.

NINGUNA funcion de este modulo esta conectada al flujo de produccion (main.py).
Importar accidentalmente este modulo no tiene efecto sobre la aplicacion
porque no registra endpoints ni modifica estado global.

Limitaciones documentadas:
  - assess_solo_level: infiere nivel SOLO de longitud y conectores causales.
    Nunca validada contra codificacion independiente por docentes.
  - _build_constructive_feedback: el docstring original decia "No genera
    calificaciones numericas"; es inexacto — la comparacion de indices
    ordinales (actual_idx vs esperado_idx) equivale a una rubrica de tres
    niveles (excelente / buen progreso / oportunidad).
  - bloom_solo_mapping: el mapeo Bloom->SOLO es un supuesto propio de los
    autores, no una correspondencia establecida por Anderson y Krathwohl
    (2001) ni por Biggs y Collis (1982).
  - TextBlob (sentimiento) era monolingue ingles; devuelve 0.0 para texto
    en espanol salvo cognados. Se retiro del flujo activo (ver P0.4).
"""

from typing import Dict, List

# Importacion local para que generate_feedback pueda llamar al clasificador activo
from .qualitative_evaluator import QualitativeEvaluator


class _DeprecatedQualitativeEvaluator:
    """Codigo legado — no instanciar en produccion."""

    SOLO_INDICATORS = {
        "preestructural": {
            "patterns": [
                "no se", "no entiendo", "confuso", "no tiene sentido",
                "creo que es", "tal vez", "no estoy seguro",
            ],
            "characteristics": [
                "Respuesta irrelevante",
                "Confusion conceptual",
                "No comprende la pregunta",
                "Usa informacion no relacionada",
            ],
            "intervention": "Revision de conceptos fundamentales necesaria",
        },
        "uniestructural": {
            "patterns": [r"^[\w\s]{10,50}$", "es cuando", "es donde", "es un"],
            "characteristics": [
                "Identifica un aspecto relevante",
                "Respuesta simple pero correcta",
                "No hace conexiones",
                "Comprension minima",
            ],
            "development": "Solicitar mas detalles y conexiones",
        },
        "multiestructural": {
            "patterns": [r"(\.|,)\s+.+(\.|,)\s+.+", "ademas", "tambien", "y"],
            "characteristics": [
                "Menciona multiples aspectos",
                "Ideas correctas pero independientes",
                "Respuesta tipo lista",
                "Falta integracion",
            ],
            "development": "Pedir relaciones entre ideas",
        },
        "relacional": {
            "patterns": [
                "porque", "debido a", "lo que causa", "se relaciona con",
                "esto significa que", "por lo tanto",
            ],
            "characteristics": [
                "Integra multiples aspectos",
                "Establece relaciones causales",
                "Comprension coherente",
                "Sistema como un todo",
            ],
            "development": "Aplicar a nuevos contextos",
        },
        "abstracto_extendido": {
            "patterns": [
                "se puede generalizar", "aplicando esto a", "en terminos generales",
                "hipotesis", "se extiende a", "principio",
            ],
            "characteristics": [
                "Generaliza a nuevos contextos",
                "Pensamiento abstracto",
                "Propone nuevas ideas",
                "Perspectivas originales",
            ],
            "development": "Fomentar investigacion independiente",
        },
    }

    @staticmethod
    def assess_solo_level(response: str, query: str) -> Dict:
        """
        Infiere nivel SOLO a partir de longitud (word_count) y presencia de
        conectores causales. Proxy superficial, no validado por docentes.
        """
        response_lower = response.lower()
        word_count = len(response.split())
        sentence_count = len([s for s in response.split(".") if s.strip()])
        has_connectors = any(
            c in response_lower
            for c in ["porque", "debido", "por lo tanto", "esto causa"]
        )
        if word_count < 15 or any(
            p in response_lower
            for p in _DeprecatedQualitativeEvaluator.SOLO_INDICATORS["preestructural"]["patterns"]
        ):
            level = "preestructural"
        elif word_count < 40 and not has_connectors:
            level = "uniestructural"
        elif sentence_count >= 2 and not has_connectors:
            level = "multiestructural"
        elif has_connectors and word_count >= 50:
            has_abstraction = any(
                p in response_lower
                for p in ["generalizar", "principio", "hipotesis", "aplicar a"]
            )
            level = "abstracto_extendido" if has_abstraction else "relacional"
        else:
            level = "multiestructural"
        solo_data = _DeprecatedQualitativeEvaluator.SOLO_INDICATORS[level]
        return {
            "nivel": level,
            "caracteristicas": solo_data["characteristics"],
            "siguiente_paso": solo_data.get("development") or solo_data.get("intervention"),
            "metricas": {
                "palabras": word_count,
                "oraciones": sentence_count,
                "tiene_conectores": has_connectors,
            },
        }

    @staticmethod
    def generate_feedback(query: str, response: str, sources: List[str]) -> Dict:
        """
        Combina clasificacion Bloom (de la pregunta) con nivel SOLO inferido
        (de la respuesta) para generar retroalimentacion.
        Nunca conectada al flujo activo de produccion.
        """
        bloom_level, bloom_desc = QualitativeEvaluator.classify_bloom_level(query)
        solo_assessment = _DeprecatedQualitativeEvaluator.assess_solo_level(response, query)
        feedback = _DeprecatedQualitativeEvaluator._build_constructive_feedback(
            bloom_level, solo_assessment, sources
        )
        return {
            "bloom": {"nivel": bloom_level, "descripcion": bloom_desc},
            "solo": solo_assessment,
            "feedback_constructivo": feedback,
            "progreso": _DeprecatedQualitativeEvaluator._determine_progress_path(
                bloom_level, solo_assessment["nivel"]
            ),
        }

    @staticmethod
    def _build_constructive_feedback(
        bloom_level: str, solo_data: Dict, sources: List[str]
    ) -> str:
        """
        Genera texto de retroalimentacion comparando nivel SOLO actual con el
        esperado para el nivel Bloom de la pregunta.

        LIMITACION: el docstring original decia "No genera calificaciones
        numericas". Es inexacto: la comparacion de indices ordinales
        (actual_idx vs esperado_idx) es equivalente a una rubrica de tres
        niveles: excelente / buen progreso / oportunidad de desarrollo.

        El bloom_solo_mapping es un supuesto de los autores, no una
        correspondencia establecida en la literatura taxonomica.
        """
        nivel_solo = solo_data["nivel"]
        bloom_solo_mapping = {
            "recordar": "uniestructural",
            "comprender": "multiestructural",
            "aplicar": "relacional",
            "analizar": "relacional",
            "evaluar": "abstracto_extendido",
            "crear": "abstracto_extendido",
        }
        esperado = bloom_solo_mapping.get(bloom_level, "multiestructural")
        nivel_orden = [
            "preestructural", "uniestructural", "multiestructural",
            "relacional", "abstracto_extendido",
        ]
        actual_idx = nivel_orden.index(nivel_solo)
        esperado_idx = nivel_orden.index(esperado)
        if actual_idx >= esperado_idx:
            feedback = (
                f"Excelente comprension: Tu respuesta demuestra nivel {nivel_solo}, "
                f"apropiado para una pregunta de nivel {bloom_level} (Bloom).\n\n"
                "Fortalezas observadas:\n"
            )
            for char in solo_data["caracteristicas"][:2]:
                feedback += f"- {char}\n"
        elif actual_idx == esperado_idx - 1:
            feedback = (
                f"Buen progreso: Tu respuesta muestra nivel {nivel_solo}. "
                f"Para una pregunta de {bloom_level}, puedes desarrollar mas.\n\n"
                f"Siguiente paso: {solo_data['siguiente_paso']}\n"
            )
        else:
            feedback = (
                f"Oportunidad de desarrollo: Tu respuesta esta en nivel {nivel_solo}. "
                f"Para abordar completamente una pregunta de {bloom_level}, se sugiere:\n\n"
                f"Accion recomendada: {solo_data['siguiente_paso']}\n"
            )
        if sources:
            feedback += f"\nFuentes consultadas: {len(sources)} documento(s)\n"
        return feedback

    @staticmethod
    def _determine_progress_path(bloom_level: str, solo_level: str) -> Dict:
        nivel_orden = [
            "preestructural", "uniestructural", "multiestructural",
            "relacional", "abstracto_extendido",
        ]
        current_idx = nivel_orden.index(solo_level)
        if current_idx < len(nivel_orden) - 1:
            next_level = nivel_orden[current_idx + 1]
            return {
                "nivel_actual": solo_level,
                "proximo_objetivo": next_level,
                "estrategias": _DeprecatedQualitativeEvaluator._get_development_strategies(
                    solo_level, next_level
                ),
            }
        return {
            "nivel_actual": solo_level,
            "proximo_objetivo": "Mantener excelencia y profundizar",
            "estrategias": ["Explorar aplicaciones avanzadas", "Investigacion independiente"],
        }

    @staticmethod
    def _get_development_strategies(current: str, target: str) -> List[str]:
        strategies_map = {
            ("preestructural", "uniestructural"): [
                "Revisar conceptos fundamentales",
                "Practicar definiciones basicas",
                "Identificar un aspecto clave a la vez",
            ],
            ("uniestructural", "multiestructural"): [
                "Agregar mas detalles",
                "Identificar aspectos adicionales",
                "Hacer listas de elementos relacionados",
            ],
            ("multiestructural", "relacional"): [
                "Conectar las ideas mencionadas",
                "Explicar relaciones causa-efecto",
                "Integrar en un todo coherente",
            ],
            ("relacional", "abstracto_extendido"): [
                "Aplicar a nuevos contextos",
                "Generalizar principios",
                "Proponer aplicaciones creativas",
            ],
        }
        return strategies_map.get((current, target), ["Continuar practicando"])
