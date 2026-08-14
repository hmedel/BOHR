"""
Motor de analisis de consultas de estudiante.

Notas sobre las limitaciones actuales (documentadas para el articulo):

analyze_sentiment: usa TextBlob con el analizador por defecto, que es
monolingue ingles. Texto en espanol produce 0.0 salvo cognados como
"horrible". Los campos sentiment_score/sentiment_label se conservan en la
BD por compatibilidad del historico pero NO se usan en decisiones
pedagogicas ni se muestran en el panel del estudiante (P0.4).

assess_complexity: usa limites de palabra (\b) a partir de esta version.
El default anterior era "intermediate", lo que inflaba ese nivel en la
distribucion y hacia que improvement_trend (que cuenta "advanced") no
fuera una medicion real. El nuevo default es "no_clasificado".
"""

from textblob import TextBlob
import json
from typing import Dict, List
import re


class AnalyticsEngine:
    """Analisis de temas y complejidad de consultas de estudiante."""

    # Palabras clave por tema.
    # Palabras compuestas: busqueda de subcadena directa.
    # Palabras simples: limite \b en detect_topics (ver abajo).
    TOPICS = {
        "estructura_atomica": [
            "atomo", "electron", "proton", "neutron", "nucleo",
            "numero atomico", "masa atomica", "isotopo",
        ],
        "mecanica_cuantica": [
            "cuantico", "cuantica", "funcion de onda", "heisenberg",
            "schrodinger", "hamiltoniano", "principio de incertidumbre", "dualidad",
        ],
        "enlaces_quimicos": [
            "enlace", "ionico", "covalente", "metalico", "molecular",
            "electronegatividad", "ligadura",
        ],
        "espectroscopia": [
            "espectro", "foton", "emision", "absorcion", "espectral",
            "longitud de onda", "frecuencia", "rydberg", "balmer",
        ],
        "orbitales": [
            "orbital", "orbital s", "orbital p", "orbital d", "orbital f",
            "hibridacion", "numero cuantico", "aufbau", "pauli", "hund",
        ],
        "termodinamica": [
            "entalpia", "entropia", "energia libre", "gibbs", "calor", "termodinamica",
        ],
        "estructura_molecular": [
            "geometria molecular", "vsepr", "momento dipolar", "polaridad", "forma molecular",
        ],
    }

    @staticmethod
    def analyze_sentiment(text: str) -> Dict:
        """
        Analiza sentimiento del texto con TextBlob (monolingue ingles).

        LIMITACION: el analizador es monolingue ingles. Para texto en espanol
        devuelve 0.0 salvo cognados. Los campos resultantes NO deben usarse
        en decisiones pedagogicas ni mostrarse al estudiante tal como estan.
        Se conservan en la BD para compatibilidad historica.
        """
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity

        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return {
            "score": round(polarity, 3),
            "label": label,
            "subjectivity": round(blob.sentiment.subjectivity, 3),
        }

    @staticmethod
    def detect_topics(text: str) -> List[str]:
        """Detecta temas usando limites de palabra para evitar falsos positivos."""
        text_lower = text.lower()
        detected = []

        for topic, keywords in AnalyticsEngine.TOPICS.items():
            for keyword in keywords:
                # Frases compuestas: busqueda directa (ya son especificas)
                if " " in keyword:
                    if keyword in text_lower:
                        detected.append(topic)
                        break
                else:
                    if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                        detected.append(topic)
                        break

        return detected

    @staticmethod
    def assess_complexity(text: str) -> str:
        """
        Evalua la complejidad de la pregunta usando limites de palabra.

        Devuelve "advanced", "intermediate", "basic" o "no_clasificado".
        El default anterior era "intermediate"; se cambia a "no_clasificado"
        para evitar inflar ese nivel en la distribucion y en improvement_trend
        (que cuenta cuantas de las ultimas 5 consultas son "advanced").
        """
        text_lower = text.lower()

        # Patrones con limite de palabra para cada nivel
        advanced_patterns = [
            r"\bhamiltoniano\b",
            r"\bfunci[oó]n de onda\b",
            r"\becuaci[oó]n\b",
            r"\bderiva\b",
            r"\bderivir\b",
            r"\bdeducir\b",
            r"\bdemostrar\b",
            r"\bdemostrar\b",
            r"\bpredecir\b",
        ]
        intermediate_patterns = [
            r"\bexplica\b",
            r"\bexplicar\b",
            r"\bdiferencia\b",
            r"\bcompara\b",
            r"\bcomparar\b",
            r"\brelaciona\b",
            r"\brelacionar\b",
            r"\banaliza\b",
            r"\banalizar\b",
        ]
        basic_patterns = [
            r"\bqu[eé] es\b",
            r"\bcu[aá]l es\b",
            r"\bdefine\b",
            r"\bdefinir\b",
            r"\bnombra\b",
            r"\benumera\b",
        ]

        if any(re.search(p, text_lower) for p in advanced_patterns):
            return "advanced"
        if any(re.search(p, text_lower) for p in intermediate_patterns):
            return "intermediate"
        if any(re.search(p, text_lower) for p in basic_patterns):
            return "basic"
        return "no_clasificado"

    @staticmethod
    def calculate_progress_metrics(user_messages: List, user_queries: List) -> Dict:
        """Calcula metricas de progreso del estudiante."""
        if not user_messages:
            return {
                "total_queries": 0,
                "avg_sentiment": 0.0,
                "topics_explored": [],
                "complexity_distribution": {},
                "improvement_trend": "neutral",
            }

        user_msgs = [m for m in user_messages if m.role == "user"]

        # avg_sentiment: se incluye por compatibilidad pero no es interpretable
        # (TextBlob monolingue ingles, ver docstring de analyze_sentiment)
        sentiments = [m.sentiment_score for m in user_msgs if m.sentiment_score is not None]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        all_topics: List[str] = []
        for m in user_msgs:
            if m.topics:
                try:
                    all_topics.extend(json.loads(m.topics))
                except Exception:
                    pass

        complexity_counts: Dict[str, int] = {
            "basic": 0, "intermediate": 0, "advanced": 0, "no_clasificado": 0,
        }
        for m in user_msgs:
            if m.query_complexity:
                complexity_counts[m.query_complexity] = (
                    complexity_counts.get(m.query_complexity, 0) + 1
                )

        # Tendencia: proporcion de "advanced" en las ultimas 5 consultas
        # (excluye no_clasificado para no distorsionar el calculo)
        trend = "comenzando"
        classified = [m for m in user_msgs if m.query_complexity in ("basic", "intermediate", "advanced")]
        if len(classified) >= 5:
            recent = classified[-5:]
            adv = sum(1 for m in recent if m.query_complexity == "advanced")
            trend = "avanzando" if adv >= 3 else "progresando" if adv >= 1 else "estable"

        return {
            "total_queries": len(user_msgs),
            "avg_sentiment": round(avg_sentiment, 3),
            "topics_explored": list(set(all_topics)),
            "complexity_distribution": complexity_counts,
            "improvement_trend": trend,
        }
