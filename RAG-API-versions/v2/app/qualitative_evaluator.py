"""
Evaluador cualitativo basado en Taxonomía de Bloom y Modelo SOLO
No genera calificaciones numéricas, solo análisis constructivo
"""

import re
from typing import Dict, List, Tuple
from textblob import TextBlob

class QualitativeEvaluator:
    """Evaluación cualitativa sin calificaciones numéricas"""
    
    # Palabras clave por nivel de Bloom
    BLOOM_KEYWORDS = {
        "recordar": {
            "keywords": ["qué es", "define", "cuál es", "lista", "enumera", "nombra"],
            "verbs": ["definir", "listar", "nombrar", "identificar", "recordar", "reconocer"],
            "description": "Recuperación de información básica"
        },
        "comprender": {
            "keywords": ["explica", "por qué", "cómo", "diferencia", "compara", "resume"],
            "verbs": ["explicar", "interpretar", "resumir", "clasificar", "comparar", "ilustrar"],
            "description": "Construcción de significado"
        },
        "aplicar": {
            "keywords": ["calcula", "resuelve", "usa", "aplica", "demuestra"],
            "verbs": ["calcular", "resolver", "aplicar", "usar", "implementar", "ejecutar"],
            "description": "Uso de procedimientos"
        },
        "analizar": {
            "keywords": ["analiza", "examina", "compara", "distingue", "relaciona"],
            "verbs": ["analizar", "examinar", "diferenciar", "organizar", "atribuir"],
            "description": "Descomposición y relaciones"
        },
        "evaluar": {
            "keywords": ["evalúa", "critica", "juzga", "argumenta", "justifica"],
            "verbs": ["evaluar", "criticar", "juzgar", "argumentar", "validar", "defender"],
            "description": "Juicios basados en criterios"
        },
        "crear": {
            "keywords": ["diseña", "crea", "propone", "inventa", "desarrolla"],
            "verbs": ["crear", "diseñar", "construir", "planificar", "producir", "formular"],
            "description": "Generación de algo nuevo"
        }
    }
    
    # Indicadores SOLO por nivel
    SOLO_INDICATORS = {
        "preestructural": {
            "patterns": [
                "no sé", "no entiendo", "confuso", "no tiene sentido",
                "creo que es", "tal vez", "no estoy seguro"
            ],
            "characteristics": [
                "Respuesta irrelevante",
                "Confusión conceptual",
                "No comprende la pregunta",
                "Usa información no relacionada"
            ],
            "intervention": "Revisión de conceptos fundamentales necesaria"
        },
        "uniestructural": {
            "patterns": [
                r"^[\w\s]{10,50}$",  # Respuestas muy cortas
                "es cuando", "es donde", "es un"
            ],
            "characteristics": [
                "Identifica un aspecto relevante",
                "Respuesta simple pero correcta",
                "No hace conexiones",
                "Comprensión mínima"
            ],
            "development": "Solicitar más detalles y conexiones"
        },
        "multiestructural": {
            "patterns": [
                r"(\.|,)\s+.+(\.|,)\s+.+",  # Múltiples ideas separadas
                "además", "también", "y"
            ],
            "characteristics": [
                "Menciona múltiples aspectos",
                "Ideas correctas pero independientes",
                "Respuesta tipo lista",
                "Falta integración"
            ],
            "development": "Pedir relaciones entre ideas"
        },
        "relacional": {
            "patterns": [
                "porque", "debido a", "lo que causa", "se relaciona con",
                "esto significa que", "por lo tanto"
            ],
            "characteristics": [
                "Integra múltiples aspectos",
                "Establece relaciones causales",
                "Comprensión coherente",
                "Sistema como un todo"
            ],
            "development": "Aplicar a nuevos contextos"
        },
        "abstracto_extendido": {
            "patterns": [
                "se puede generalizar", "aplicando esto a", "en términos generales",
                "hipótesis", "se extiende a", "principio"
            ],
            "characteristics": [
                "Generaliza a nuevos contextos",
                "Pensamiento abstracto",
                "Propone nuevas ideas",
                "Perspectivas originales"
            ],
            "development": "Fomentar investigación independiente"
        }
    }
    
    @staticmethod
    def classify_bloom_level(query: str) -> Tuple[str, str]:
        """
        Clasificar el nivel de Bloom de una pregunta
        Returns: (nivel, descripción)
        """
        query_lower = query.lower()
        
        # Orden de verificación: de más específico a más general
        for level in ["crear", "evaluar", "analizar", "aplicar", "comprender", "recordar"]:
            level_data = QualitativeEvaluator.BLOOM_KEYWORDS[level]
            
            # Verificar keywords
            if any(kw in query_lower for kw in level_data["keywords"]):
                return level, level_data["description"]
            
            # Verificar verbos
            if any(verb in query_lower for verb in level_data["verbs"]):
                return level, level_data["description"]
        
        # Default: comprender
        return "comprender", "Construcción de significado"
    
    @staticmethod
    def assess_solo_level(response: str, query: str) -> Dict:
        """
        Evaluar el nivel SOLO de una respuesta
        Returns: dict con nivel, características e indicadores
        """
        response_lower = response.lower()
        
        # Calcular métricas básicas
        word_count = len(response.split())
        sentence_count = len([s for s in response.split('.') if s.strip()])
        has_connectors = any(conn in response_lower for conn in ["porque", "debido", "por lo tanto", "esto causa"])
        
        # Detectar nivel
        if word_count < 15 or any(p in response_lower for p in QualitativeEvaluator.SOLO_INDICATORS["preestructural"]["patterns"]):
            level = "preestructural"
        elif word_count < 40 and not has_connectors:
            level = "uniestructural"
        elif sentence_count >= 2 and not has_connectors:
            level = "multiestructural"
        elif has_connectors and word_count >= 50:
            # Distinguir entre relacional y abstracto extendido
            has_abstraction = any(p in response_lower for p in ["generalizar", "principio", "hipótesis", "aplicar a"])
            level = "abstracto_extendido" if has_abstraction else "relacional"
        else:
            level = "multiestructural"  # default intermedio
        
        solo_data = QualitativeEvaluator.SOLO_INDICATORS[level]
        
        return {
            "nivel": level,
            "caracteristicas": solo_data["characteristics"],
            "siguiente_paso": solo_data.get("development") or solo_data.get("intervention"),
            "metricas": {
                "palabras": word_count,
                "oraciones": sentence_count,
                "tiene_conectores": has_connectors
            }
        }
    
    @staticmethod
    def generate_feedback(query: str, response: str, sources: List[str]) -> Dict:
        """
        Generar retroalimentación cualitativa completa
        """
        # Clasificar pregunta (Bloom)
        bloom_level, bloom_desc = QualitativeEvaluator.classify_bloom_level(query)
        
        # Evaluar respuesta (SOLO)
        solo_assessment = QualitativeEvaluator.assess_solo_level(response, query)
        
        # Generar feedback constructivo
        feedback = QualitativeEvaluator._build_constructive_feedback(
            bloom_level, solo_assessment, sources
        )
        
        return {
            "bloom": {
                "nivel": bloom_level,
                "descripcion": bloom_desc
            },
            "solo": solo_assessment,
            "feedback_constructivo": feedback,
            "progreso": QualitativeEvaluator._determine_progress_path(bloom_level, solo_assessment["nivel"])
        }
    
    @staticmethod
    def _build_constructive_feedback(bloom_level: str, solo_data: Dict, sources: List[str]) -> str:
        """Construir mensaje de retroalimentación sin calificación numérica"""
        
        nivel_solo = solo_data["nivel"]
        
        # Mapeo Bloom-SOLO esperado
        bloom_solo_mapping = {
            "recordar": "uniestructural",
            "comprender": "multiestructural",
            "aplicar": "relacional",
            "analizar": "relacional",
            "evaluar": "abstracto_extendido",
            "crear": "abstracto_extendido"
        }
        
        esperado = bloom_solo_mapping.get(bloom_level, "multiestructural")
        
        # Niveles ordinales
        nivel_orden = ["preestructural", "uniestructural", "multiestructural", "relacional", "abstracto_extendido"]
        actual_idx = nivel_orden.index(nivel_solo)
        esperado_idx = nivel_orden.index(esperado)
        
        if actual_idx >= esperado_idx:
            feedback = f"🎯 **Excelente comprensión**: Tu respuesta demuestra nivel **{nivel_solo}**, "
            feedback += f"que es apropiado para una pregunta de nivel **{bloom_level}** (Bloom).\n\n"
            feedback += f"**Fortalezas observadas:**\n"
            for char in solo_data["caracteristicas"][:2]:
                feedback += f"- {char}\n"
        elif actual_idx == esperado_idx - 1:
            feedback = f"✅ **Buen progreso**: Tu respuesta muestra nivel **{nivel_solo}**. "
            feedback += f"Para una pregunta de **{bloom_level}**, podrías desarrollar más.\n\n"
            feedback += f"**Siguiente paso:** {solo_data['siguiente_paso']}\n"
        else:
            feedback = f"📚 **Oportunidad de desarrollo**: Tu respuesta está en nivel **{nivel_solo}**. "
            feedback += f"Para abordar completamente una pregunta de **{bloom_level}**, te sugiero:\n\n"
            feedback += f"**Acción recomendada:** {solo_data['siguiente_paso']}\n"
        
        # Mencionar fuentes consultadas
        if sources:
            feedback += f"\n📖 **Fuentes consultadas:** {len(sources)} documento(s)\n"
        
        return feedback
    
    @staticmethod
    def _determine_progress_path(bloom_level: str, solo_level: str) -> Dict:
        """Determinar camino de progreso personalizado"""
        
        nivel_orden = ["preestructural", "uniestructural", "multiestructural", "relacional", "abstracto_extendido"]
        current_idx = nivel_orden.index(solo_level)
        
        if current_idx < len(nivel_orden) - 1:
            next_level = nivel_orden[current_idx + 1]
            return {
                "nivel_actual": solo_level,
                "proximo_objetivo": next_level,
                "estrategias": QualitativeEvaluator._get_development_strategies(solo_level, next_level)
            }
        else:
            return {
                "nivel_actual": solo_level,
                "proximo_objetivo": "Mantener excelencia y profundizar",
                "estrategias": ["Explorar aplicaciones avanzadas", "Investigación independiente"]
            }
    
    @staticmethod
    def _get_development_strategies(current: str, target: str) -> List[str]:
        """Obtener estrategias específicas de desarrollo"""
        strategies_map = {
            ("preestructural", "uniestructural"): [
                "Revisar conceptos fundamentales",
                "Practicar definiciones básicas",
                "Identificar un aspecto clave a la vez"
            ],
            ("uniestructural", "multiestructural"): [
                "Agregar más detalles",
                "Identificar aspectos adicionales",
                "Hacer listas de elementos relacionados"
            ],
            ("multiestructural", "relacional"): [
                "Conectar las ideas mencionadas",
                "Explicar relaciones causa-efecto",
                "Integrar en un todo coherente"
            ],
            ("relacional", "abstracto_extendido"): [
                "Aplicar a nuevos contextos",
                "Generalizar principios",
                "Proponer aplicaciones creativas"
            ]
        }
        
        return strategies_map.get((current, target), ["Continuar practicando"])
