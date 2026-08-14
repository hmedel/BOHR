"""
Evaluador cualitativo basado en Taxonomia de Bloom.

Solo classify_bloom_level esta conectada al flujo de produccion (main.py
lineas 633 y 996). El resto del modulo es codigo legado no conectado; se
conserva en la seccion DEPRECATED al final del archivo para referencia, con
documentacion de lo que mide realmente cada funcion.

Nota metodologica: el mapeo Bloom-SOLO que aparece en _build_constructive_feedback
es un supuesto propio de los autores de este sistema, no una correspondencia
establecida por Anderson y Krathwohl (2001) ni por Biggs y Collis (1982).
"""

import re
from typing import Dict, List, Tuple


class QualitativeEvaluator:
    """Clasificacion de nivel Bloom para preguntas de estudiante."""

    # Palabras clave por nivel de Bloom.
    # Criterios de inclusion:
    #   - Cada termino debe aparecer como palabra completa (limite \b) para
    #     evitar colisiones con vocabulario disciplinar de quimica:
    #       "causa" contiene "usa"  -> disparaba "aplicar" erroneamente
    #       "principio" contiene "principio" y aparece en SOLO pero
    #       tambien en vocabulario cuantico ("principio de exclusion")
    #   - Terminos duplicados entre niveles se asignan al nivel mas alto
    #     en el orden de recorrido: crear > evaluar > analizar > aplicar >
    #     comprender > recordar.
    #   - Verbos anadidos: deducir, predecir, justificar, derivar, estimar,
    #     interpretar (uso real en preguntas del curso).
    BLOOM_KEYWORDS: Dict[str, Dict] = {
        "recordar": {
            "keywords": [
                r"\bqu[eé] es\b",
                r"\bdefine\b",
                r"\bcu[aá]l es\b",
                r"\blista\b",
                r"\benumera\b",
                r"\bnombra\b",
            ],
            "verbs": [
                r"\bdefinir\b",
                r"\blistar\b",
                r"\bnombrar\b",
                r"\bidentificar\b",
                r"\brecordar\b",
                r"\breconocer\b",
            ],
            "description": "Recuperacion de informacion basica",
        },
        "comprender": {
            "keywords": [
                r"\bexplica\b",
                r"\bpor qu[eé]\b",
                r"\bc[oó]mo\b",
                r"\bdiferencia\b",
                r"\bcompara\b",
                r"\bresume\b",
                r"\binterpretar\b",
            ],
            "verbs": [
                r"\bexplicar\b",
                r"\binterpretar\b",
                r"\bresumir\b",
                r"\bclasificar\b",
                r"\bcomparar\b",
                r"\bilustrar\b",
            ],
            "description": "Construccion de significado",
        },
        "aplicar": {
            # "usa" y "aplica" son palabras completas; sin \b colisionaban con
            # "causa", "aplica a bosones", etc.
            "keywords": [
                r"\bcalcula\b",
                r"\bresuelve\b",
                r"\busa\b",
                r"\baplica\b",
                r"\bdemuestra\b",
                r"\bestima\b",
            ],
            "verbs": [
                r"\bcalcular\b",
                r"\bresolver\b",
                r"\baplicar\b",
                r"\busar\b",
                r"\bimplementar\b",
                r"\bejecutar\b",
                r"\bestimar\b",
            ],
            "description": "Uso de procedimientos",
        },
        "analizar": {
            "keywords": [
                r"\banaliza\b",
                r"\bexamina\b",
                r"\bdistingue\b",
                r"\brelaciona\b",
                r"\bdeduce\b",
                r"\bpredice\b",
            ],
            "verbs": [
                r"\banalizar\b",
                r"\bexaminar\b",
                r"\bdiferenciar\b",
                r"\borganizar\b",
                r"\batribuir\b",
                r"\bdeducir\b",
                r"\bpredecir\b",
                r"\bderiva\b",
                r"\bderivir\b",
            ],
            "description": "Descomposicion y relaciones",
        },
        "evaluar": {
            "keywords": [
                r"\bev[aá]l[uú]a\b",
                r"\bcritica\b",
                r"\bjuzga\b",
                r"\bargumenta\b",
                r"\bjustifica\b",
            ],
            "verbs": [
                r"\bevaluar\b",
                r"\bcriticar\b",
                r"\bjuzgar\b",
                r"\bargumentar\b",
                r"\bvalidar\b",
                r"\bdefender\b",
                r"\bjustificar\b",
            ],
            "description": "Juicios basados en criterios",
        },
        "crear": {
            "keywords": [
                r"\bdisenha\b",
                r"\bcrea\b",
                r"\bpropone\b",
                r"\binventa\b",
                r"\bdesarrolla\b",
            ],
            "verbs": [
                r"\bcrear\b",
                r"\bdisenhar\b",
                r"\bconstruir\b",
                r"\bplanificar\b",
                r"\bproducir\b",
                r"\bformular\b",
            ],
            "description": "Generacion de algo nuevo",
        },
    }

    @staticmethod
    def classify_bloom_level(query: str) -> Tuple[str, str]:
        """
        Clasifica el nivel de Bloom de una pregunta usando limites de palabra.

        Returns:
            (nivel, descripcion) donde nivel puede ser uno de los seis niveles
            de Bloom o "no_clasificado" si ninguna palabra clave hace match.
            "no_clasificado" reemplaza el antiguo default "comprender" para
            evitar inflar artificialmente ese nivel en la distribucion del panel.
        """
        query_lower = query.lower()

        # Orden: mas especifico primero (crear requiere mayor habilidad cognitiva)
        for level in ["crear", "evaluar", "analizar", "aplicar", "comprender", "recordar"]:
            level_data = QualitativeEvaluator.BLOOM_KEYWORDS[level]

            for pattern in level_data["keywords"]:
                if re.search(pattern, query_lower):
                    return level, level_data["description"]

            for pattern in level_data["verbs"]:
                if re.search(pattern, query_lower):
                    return level, level_data["description"]

        return "no_clasificado", "Pregunta sin marcadores lexicos de nivel Bloom"


# =============================================================================
# DEPRECATED — codigo no conectado al flujo de produccion
# =============================================================================
# Las funciones siguientes no son invocadas desde main.py ni desde ningun
# endpoint activo. Se conservan para referencia historica y para documentar
# que median realmente.
#
# assess_solo_level: infiere nivel SOLO a partir de longitud de respuesta y
#   presencia de conectores causales. No fue validada contra codificacion
#   independiente por docentes. El mapeo Bloom->SOLO de _build_constructive_feedback
#   es un supuesto de los autores, no una correspondencia establecida.
#
# generate_feedback / _build_constructive_feedback: generaban texto de
#   retroalimentacion combinando el nivel Bloom de la pregunta y el nivel SOLO
#   inferido de la respuesta. El docstring "No genera calificaciones numericas"
#   es inexacto: la comparacion de indices ordinales en _build_constructive_feedback
#   es una rubrica de tres niveles (excelente / buen progreso / oportunidad).
#
# _determine_progress_path / _get_development_strategies: producian
#   recomendaciones de siguiente paso segun nivel SOLO actual.
#
# TextBlob se importaba unicamente para las funciones deprecated; se retira
# del import activo para evitar confusion sobre el estado del analisis de
# sentimiento (ver analytics_engine.py, funcion analyze_sentiment).
# =============================================================================

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
        # Nota: esta comparacion de indices ordinales equivale a una rubrica
        # de tres niveles. El docstring original "sin calificaciones numericas"
        # es inexacto.
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
