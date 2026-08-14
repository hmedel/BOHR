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
# DEPRECATED — codigo movido a app/_legacy_qualitative.py
# =============================================================================
# Las funciones assess_solo_level, generate_feedback, _build_constructive_feedback,
# _determine_progress_path y _get_development_strategies no son invocadas desde
# ningun endpoint activo. Se movieron a _legacy_qualitative.py para mantener
# este archivo enfocado en el clasificador Bloom activo.
#
# Ver _legacy_qualitative.py para la documentacion detallada de lo que
# median realmente esas funciones y sus limitaciones metodologicas.
# =============================================================================
