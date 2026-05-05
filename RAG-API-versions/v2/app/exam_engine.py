"""
Motor de Exámenes Conversacional
Genera UNA pregunta a la vez, recibe respuesta, da feedback, siguiente pregunta
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class ExamEngine:
    """Generación y evaluación de exámenes conversacionales"""
    
    @staticmethod
    def should_offer_exam(conversation_messages: List) -> Dict:
        """Determinar si se debe ofrecer un examen"""
        user_messages = [m for m in conversation_messages if m.role == "user"]
        
        if len(user_messages) < 3:
            return {
                "should_offer": False,
                "reason": "Necesitas al menos 3 consultas para generar un examen significativo"
            }
        
        topics_covered = set()
        for msg in user_messages:
            if msg.topics:
                try:
                    topics = json.loads(msg.topics)
                    topics_covered.update(topics)
                except:
                    pass
        
        if len(topics_covered) < 2:
            return {
                "should_offer": False,
                "reason": "Explora al menos 2 temas diferentes antes del examen"
            }
        
        return {
            "should_offer": True,
            "topics_covered": list(topics_covered),
            "queries_count": len(user_messages),
            "recommendation": "¡Excelente progreso! Estás listo para un examen formativo."
        }
    
    @staticmethod
    def get_difficulty_profile(past_exams_results: List[Dict]) -> Dict:
        """
        Analiza exámenes anteriores para calcular el perfil de dificultad del siguiente.
        Devuelve: nivel_inicio, nivel_maximo, porcentaje_correcto_historico
        """
        if not past_exams_results:
            return {"nivel_inicio": "comprender", "nivel_maximo": "analizar", "pct_historico": None}

        # Calcular tasa de acierto histórica
        total_correct = sum(r.get("correct", 0) for r in past_exams_results)
        total_q = sum(r.get("total", 0) for r in past_exams_results)
        pct = total_correct / total_q if total_q else 0

        # Subir dificultad si el estudiante va bien, bajar si va mal
        if pct >= 0.8:
            return {"nivel_inicio": "aplicar",   "nivel_maximo": "crear",    "pct_historico": pct}
        elif pct >= 0.6:
            return {"nivel_inicio": "comprender", "nivel_maximo": "evaluar",  "pct_historico": pct}
        else:
            return {"nivel_inicio": "recordar",   "nivel_maximo": "aplicar",  "pct_historico": pct}

    @staticmethod
    def generate_single_question_prompt(
        conversation_history: List,
        topics: List[str],
        question_number: int,
        total_questions: int,
        previous_levels: List[str] = [],
        difficulty_profile: Optional[Dict] = None,
    ) -> str:
        """Generar prompt para UNA pregunta"""

        # Extraer conceptos principales
        concepts = []
        for msg in conversation_history:
            if msg.role == "user":
                concepts.append(msg.content[:80])

        concepts_summary = "\n".join([f"- {c}" for c in concepts[:8]])
        topics_summary = ", ".join(topics)

        # Perfil de dificultad
        profile = difficulty_profile or {"nivel_inicio": "comprender", "nivel_maximo": "analizar"}
        bloom_progression = ["recordar", "comprender", "aplicar", "analizar", "evaluar", "crear"]
        start_idx = bloom_progression.index(profile["nivel_inicio"]) if profile["nivel_inicio"] in bloom_progression else 1
        max_idx   = bloom_progression.index(profile["nivel_maximo"])  if profile["nivel_maximo"]  in bloom_progression else 3

        # Distribuir niveles progresivamente dentro del rango permitido
        range_size = max(1, max_idx - start_idx)
        step = range_size / max(1, total_questions - 1)
        target_idx = min(max_idx, round(start_idx + (question_number - 1) * step))
        target_level = bloom_progression[target_idx]

        # No repetir nivel si ya se usó
        if target_level in previous_levels:
            for candidate in bloom_progression[target_idx:max_idx+1]:
                if candidate not in previous_levels:
                    target_level = candidate
                    break

        # Nota de contexto histórico para el LLM
        history_note = ""
        if profile.get("pct_historico") is not None:
            pct_str = f"{profile['pct_historico']:.0%}"
            history_note = f"\n**Nota:** El estudiante obtuvo {pct_str} en exámenes anteriores. Ajusta la dificultad al nivel {target_level} en consecuencia."
        
        return f"""# GENERACIÓN DE PREGUNTA DE EXAMEN FORMATIVO

## CONTEXTO
**Pregunta {question_number} de {total_questions}**
**Temas estudiados:** {topics_summary}
**Conceptos del estudiante:**
{concepts_summary}{history_note}

## INSTRUCCIONES CRÍTICAS

Genera UNA SOLA PREGUNTA de **opción múltiple** (preferentemente) o desarrollo corto.

**Nivel objetivo:** {target_level}

### FORMATO JSON ESTRICTO
```json
{{
  "numero": {question_number},
  "nivel_bloom": "{target_level}",
  "tipo": "opcion_multiple",
  "enunciado": "[Pregunta clara y específica sobre lo que estudió]",
  "opciones": [
    "A) [opción plausible]",
    "B) [opción plausible]",
    "C) [opción plausible]",
    "D) [opción correcta pero no obvia]"
  ],
  "_respuesta_correcta": "D",
  "_justificacion": "[Por qué D es correcta y las otras no]",
  "_conceptos_clave": [
    "Debe identificar [concepto X]",
    "Debe distinguir entre [A y B]"
  ],
  "criterios_evaluacion": {{
    "excelente": "Identifica correctamente y justifica con claridad",
    "bueno": "Identifica correctamente pero justificación básica",
    "regular": "Duda entre opciones correctas",
    "insuficiente": "Confunde conceptos fundamentales"
  }},
  "recursos_estudio": [
    "Revisar [concepto específico del tema]",
    "Repasar [sección específica]"
  ]
}}
```

### REQUISITOS
- ✅ Opciones múltiples balanceadas (todas plausibles)
- ✅ Basada en lo que el estudiante REALMENTE estudió
- ✅ Clara y sin ambigüedades
- ✅ Respuesta correcta no debe ser obvia
- ❌ NO revelar la respuesta en el enunciado
- ❌ NO usar lenguaje técnico innecesario

GENERA SOLO EL JSON, SIN TEXTO ADICIONAL:"""
    
    @staticmethod
    def parse_question_from_llm(llm_response: str) -> Optional[Dict]:
        """Extraer JSON de pregunta de la respuesta del LLM"""
        try:
            # Limpiar respuesta
            response = llm_response.strip()
            
            # Intentar extraer JSON de markdown
            if "```json" in response:
                json_match = re.search(r'```json\s*\n([\s\S]+?)\n```', response)
                if json_match:
                    response = json_match.group(1)
            elif "```" in response:
                json_match = re.search(r'```\s*\n([\s\S]+?)\n```', response)
                if json_match:
                    response = json_match.group(1)
            
            # Buscar JSON directo
            json_match = re.search(r'\{[\s\S]+\}', response)
            if json_match:
                response = json_match.group(0)
            
            question_data = json.loads(response)
            return question_data
            
        except Exception as e:
            print(f"Error parsing question: {e}")
            return None
    
    @staticmethod
    def evaluate_answer(
        question: Dict,
        student_answer: str,
        is_correct: Optional[bool] = None
    ) -> Dict:
        """
        Evaluar respuesta del estudiante SIN revelar la correcta
        """
        
        # Determinar si es correcta (si es opción múltiple)
        if question.get("tipo") == "opcion_multiple":
            correct_letter = question.get("_respuesta_correcta", "").upper().strip()
            student_letter = student_answer.strip().upper()[0] if student_answer else ""
            is_correct = (student_letter == correct_letter)
        
        # Criterios de evaluación
        criterios = question.get("criterios_evaluacion", {})
        
        # Generar feedback según resultado
        if is_correct:
            nivel = "excelente" if len(student_answer) > 20 else "bueno"
            feedback_base = criterios.get(nivel, "Respuesta correcta")
            
            feedback = f"""### ✅ Respuesta Correcta

{feedback_base}

**Por qué es correcto:**
Has demostrado comprensión del concepto. Tu respuesta indica que identificaste los elementos clave.

**Fortalezas observadas:**
- Identificación correcta del concepto
- Comprensión adecuada del tema

**Para profundizar aún más:**
"""
            for recurso in question.get("recursos_estudio", [])[:2]:
                feedback += f"- {recurso}\n"
            
        else:
            nivel = "insuficiente"
            feedback_base = criterios.get(nivel, "Revisa los conceptos fundamentales")
            
            feedback = f"""### 🔍 Oportunidad de Aprendizaje

{feedback_base}

**Áreas de reflexión:**
No te preocupes, el error es parte del aprendizaje. Esta pregunta toca conceptos importantes.

**Te recomiendo:**
"""
            for recurso in question.get("recursos_estudio", []):
                feedback += f"- {recurso}\n"
            
            feedback += f"""
**Conceptos clave a repasar:**
"""
            for concepto in question.get("_conceptos_clave", [])[:2]:
                # Generalizar sin revelar respuesta
                concepto_sin_revelar = concepto.split("Debe ")[1] if "Debe " in concepto else concepto
                feedback += f"- {concepto_sin_revelar}\n"
        
        return {
            "is_correct": is_correct,
            "nivel": "excelente" if is_correct else "insuficiente",
            "feedback": feedback,
            "recursos_recomendados": question.get("recursos_estudio", [])
        }
    
    @staticmethod
    def generate_final_summary(
        questions_and_answers: List[Dict],
        topics_covered: List[str]
    ) -> str:
        """Generar resumen final del examen"""
        
        total_questions = len(questions_and_answers)
        correct_count = sum(1 for qa in questions_and_answers if qa.get("evaluation", {}).get("is_correct", False))
        
        # Análisis por nivel Bloom
        bloom_distribution = {}
        for qa in questions_and_answers:
            nivel = qa.get("question", {}).get("nivel_bloom", "desconocido")
            bloom_distribution[nivel] = bloom_distribution.get(nivel, 0) + 1
        
        # Generar recomendaciones
        if correct_count == total_questions:
            nivel_global = "🌟 Excelente comprensión"
            descripcion = "Demuestras dominio sólido de los conceptos estudiados. Has alcanzado los objetivos de aprendizaje."
        elif correct_count >= total_questions * 0.7:
            nivel_global = "✅ Buena comprensión"
            descripcion = "Tienes una base sólida. Con un poco más de práctica alcanzarás el dominio completo."
        elif correct_count >= total_questions * 0.5:
            nivel_global = "📚 Comprensión en desarrollo"
            descripcion = "Estás construyendo tu conocimiento. Dedica tiempo a repasar los conceptos fundamentales."
        else:
            nivel_global = "🌱 Iniciando el aprendizaje"
            descripcion = "Estás en las etapas iniciales. No te desanimes, todos comenzamos aquí. Enfócate en los conceptos básicos."
        
        summary = f"""# 🎓 Resumen de tu Examen Formativo

## {nivel_global}

{descripcion}

---

## 📊 Resultados

**Preguntas respondidas:** {total_questions}
**Respuestas correctas:** {correct_count}

### Distribución por Nivel Bloom
"""
        
        for nivel, count in bloom_distribution.items():
            summary += f"- **{nivel.title()}:** {count} pregunta(s)\n"
        
        summary += f"""
---

## 💡 Análisis Cualitativo

**Temas cubiertos en el examen:**
"""
        for topic in topics_covered[:5]:
            summary += f"- {topic}\n"
        
        # Fortalezas y áreas de mejora
        summary += """
---

## ✨ Fortalezas Observadas

"""
        if correct_count > 0:
            summary += f"- Has demostrado comprensión en {correct_count} de {total_questions} preguntas\n"
            summary += "- Capacidad para identificar conceptos clave\n"
            if correct_count >= total_questions * 0.7:
                summary += "- Buen nivel de retención de información\n"
        else:
            summary += "- Has completado el examen, lo cual es el primer paso\n"
            summary += "- Has identificado áreas específicas de estudio\n"
        
        summary += """
---

## 📈 Plan de Acción Personalizado

"""
        
        if correct_count == total_questions:
            summary += """**Objetivo:** Profundizar y aplicar conocimientos

**Acciones recomendadas:**
1. Explorar aplicaciones avanzadas de los conceptos
2. Resolver problemas más complejos
3. Conectar con otros temas relacionados
4. Considerar proyectos de aplicación práctica

**Tiempo estimado:** 1-2 semanas de práctica avanzada
"""
        elif correct_count >= total_questions * 0.7:
            summary += """**Objetivo:** Consolidar y reforzar

**Acciones recomendadas:**
1. Repasar preguntas donde tuviste dificultad
2. Practicar con ejercicios similares
3. Profundizar en conceptos específicos
4. Relacionar conceptos entre sí

**Tiempo estimado:** 1 semana de repaso enfocado
"""
        else:
            summary += """**Objetivo:** Fortalecer fundamentos

**Acciones recomendadas:**
1. Revisar conceptos básicos del tema
2. Estudiar con ejemplos simples paso a paso
3. Practicar con ejercicios guiados
4. Consultar material introductorio
5. Considerar sesiones de estudio adicionales

**Tiempo estimado:** 2-3 semanas de estudio consistente
"""
        
        summary += """
---

## 🔄 Próximos Pasos

1. **Revisa los recursos sugeridos** en cada pregunta
2. **Practica** con ejercicios adicionales
3. **Consulta** cuando tengas dudas
4. **Vuelve a intentar** cuando te sientas preparado

---

💡 **Recuerda:** Este examen es formativo, no sumativo. Su objetivo es ayudarte a identificar qué sabes y qué necesitas reforzar. El aprendizaje es un proceso continuo.

¿Deseas comenzar una nueva conversación o profundizar en algún tema específico?
"""
        
        return summary
