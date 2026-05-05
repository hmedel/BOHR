from textblob import TextBlob
import json
from typing import Dict, List
import re

class AnalyticsEngine:
    """Motor de análisis de sentimiento y tracking"""
    
    # Palabras clave por tema (solo palabras completas para evitar falsos positivos)
    TOPICS = {
        "estructura_atomica": ["átomo", "electrón", "protón", "neutrón", "núcleo", "número atómico", "masa atómica", "isótopo"],
        "mecanica_cuantica": ["cuántico", "cuántica", "función de onda", "heisenberg", "schrödinger", "hamiltoniano", "principio de incertidumbre", "dualidad"],
        "enlaces_quimicos": ["enlace", "iónico", "covalente", "metálico", "molecular", "electronegatividad", "ligadura"],
        "espectroscopia": ["espectro", "fotón", "emisión", "absorción", "espectral", "longitud de onda", "frecuencia", "rydberg", "balmer"],
        "orbitales": ["orbital", "orbital s", "orbital p", "orbital d", "orbital f", "hibridación", "número cuántico", "aufbau", "pauli", "hund"],
        "termodinamica": ["entalpía", "entropía", "energía libre", "gibbs", "calor", "termodinámica"],
        "estructura_molecular": ["geometría molecular", "vsepr", "momento dipolar", "polaridad", "forma molecular"],
    }
    
    @staticmethod
    def analyze_sentiment(text: str) -> Dict:
        """Analizar sentimiento del texto"""
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 a 1
        
        # Clasificar
        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"
        
        return {
            "score": round(polarity, 3),
            "label": label,
            "subjectivity": round(blob.sentiment.subjectivity, 3)
        }
    
    @staticmethod
    def detect_topics(text: str) -> List[str]:
        """Detectar temas en la consulta usando coincidencia de palabras completas"""
        text_lower = text.lower()
        detected = []

        for topic, keywords in AnalyticsEngine.TOPICS.items():
            for keyword in keywords:
                # Palabras compuestas: búsqueda directa; palabras simples: solo como palabra completa
                if " " in keyword:
                    if keyword in text_lower:
                        detected.append(topic)
                        break
                else:
                    if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                        detected.append(topic)
                        break

        return detected
    
    @staticmethod
    def assess_complexity(text: str) -> str:
        """Evaluar complejidad de la pregunta"""
        text_lower = text.lower()
        
        # Indicadores de complejidad
        advanced_words = ["hamiltoniano", "función de onda", "ecuación", "derivar", "demostrar"]
        intermediate_words = ["explica", "diferencia", "compara", "relaciona"]
        basic_words = ["qué es", "cuál es", "define"]
        
        if any(word in text_lower for word in advanced_words):
            return "advanced"
        elif any(word in text_lower for word in intermediate_words):
            return "intermediate"
        elif any(word in text_lower for word in basic_words):
            return "basic"
        else:
            return "intermediate"  # default
    
    @staticmethod
    def calculate_progress_metrics(user_messages: List, user_queries: List) -> Dict:
        """Calcular métricas de progreso del estudiante"""
        if not user_messages:
            return {
                "total_queries": 0,
                "avg_sentiment": 0.0,
                "topics_explored": [],
                "complexity_distribution": {},
                "improvement_trend": "neutral"
            }
        
        # Filtrar solo mensajes del usuario
        user_msgs = [m for m in user_messages if m.role == "user"]
        
        # Sentimiento promedio
        sentiments = [m.sentiment_score for m in user_msgs if m.sentiment_score is not None]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        # Temas explorados
        all_topics = []
        for m in user_msgs:
            if m.topics:
                try:
                    topics = json.loads(m.topics)
                    all_topics.extend(topics)
                except:
                    pass
        
        unique_topics = list(set(all_topics))
        
        # Distribución de complejidad
        complexity_counts = {"basic": 0, "intermediate": 0, "advanced": 0}
        for m in user_msgs:
            if m.query_complexity:
                complexity_counts[m.query_complexity] = complexity_counts.get(m.query_complexity, 0) + 1
        
        # Tendencia de mejora (simplificada: más preguntas avanzadas = mejora)
        if len(user_msgs) >= 5:
            recent = user_msgs[-5:]
            advanced_recent = sum(1 for m in recent if m.query_complexity == "advanced")
            if advanced_recent >= 3:
                trend = "improving"
            elif advanced_recent <= 1:
                trend = "stable"
            else:
                trend = "progressing"
        else:
            trend = "starting"
        
        return {
            "total_queries": len(user_msgs),
            "avg_sentiment": round(avg_sentiment, 3),
            "topics_explored": unique_topics,
            "complexity_distribution": complexity_counts,
            "improvement_trend": trend
        }
