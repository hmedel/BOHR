"""
Motor de Exámenes Conversacional
Genera UNA pregunta a la vez, recibe respuesta, da feedback, siguiente pregunta
"""

import json
import random
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class ExamEngine:
    """Generación y evaluación de exámenes conversacionales"""
    
    @staticmethod
    def should_offer_exam(conversation_messages: List) -> Dict:
        """Determinar si se debe ofrecer un examen.

        Umbral: 5 mensajes de usuario y al menos 2 temas distintos.
        (Version anterior usaba 3; main.py usaba 5; se unifica aqui en 5,
        que es el valor documentado en BOHR_idea.md y en CLAUDE.md.)
        """
        user_messages = [m for m in conversation_messages if m.role == "user"]

        if len(user_messages) < 5:
            return {
                "should_offer": False,
                "reason": "Necesitas al menos 5 consultas para generar un examen significativo",
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
        evidence_passages: Optional[List[Dict]] = None,
    ) -> str:
        """
        Genera el prompt para UNA pregunta fundamentada en pasajes del corpus.

        Si evidence_passages no es None y contiene pasajes, el modelo recibe
        la instruccion de construir enunciado, opciones y justificacion
        EXCLUSIVAMENTE a partir de esos pasajes, y de devolver
        {"error": "evidencia_insuficiente"} si la evidencia no alcanza.

        Si evidence_passages es None o vacio (p.ej. Ollama no disponible),
        el prompt se genera sin evidencia — comportamiento anterior, degradado
        con advertencia.
        """

        # Extraer conceptos principales de la sesion
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

        range_size = max(1, max_idx - start_idx)
        step = range_size / max(1, total_questions - 1)
        target_idx = min(max_idx, round(start_idx + (question_number - 1) * step))
        target_level = bloom_progression[target_idx]

        if target_level in previous_levels:
            for candidate in bloom_progression[target_idx:max_idx+1]:
                if candidate not in previous_levels:
                    target_level = candidate
                    break

        history_note = ""
        if profile.get("pct_historico") is not None:
            pct_str = f"{profile['pct_historico']:.0%}"
            history_note = f"\n**Nota:** El estudiante obtuvo {pct_str} en examenes anteriores. Ajusta la dificultad al nivel {target_level} en consecuencia."

        # ── Bloque de evidencia ──────────────────────────────────────────────
        if evidence_passages:
            evidence_block = "\n\n".join(
                f"[Pasaje {i+1} — Fuente: {p['source']}]\n{p['text']}"
                for i, p in enumerate(evidence_passages)
            )
            evidence_section = f"""
## EVIDENCIA DISPONIBLE (fragmentos del corpus de la asignatura)

{evidence_block}

---
"""
            fundamento_instruccion = """## INSTRUCCION FUNDAMENTAL

Construye el enunciado, la opcion correcta, los distractores y la
justificacion EXCLUSIVAMENTE a partir de los pasajes de EVIDENCIA DISPONIBLE.
No uses conocimiento externo al corpus proporcionado.

Si la evidencia no es suficiente para formular una pregunta del nivel
objetivo sin inventar informacion, devuelve exactamente:
{"error": "evidencia_insuficiente"}

En el JSON de salida, los campos pasaje_fuente y documento_fuente deben
identificar el pasaje concreto del que se extrae la pregunta.
"""
        else:
            evidence_section = ""
            fundamento_instruccion = """## ADVERTENCIA

No se proporcionaron pasajes del corpus. Genera la pregunta basandote
en los temas estudiados, pero ten en cuenta que esta pregunta no
podra ser auditada contra el material de la asignatura.
"""

        return f"""# GENERACION DE PREGUNTA DE EXAMEN FORMATIVO

## CONTEXTO
**Pregunta {question_number} de {total_questions}**
**Temas estudiados:** {topics_summary}
**Conceptos explorados por el estudiante:**
{concepts_summary}{history_note}
{evidence_section}
{fundamento_instruccion}

Genera UNA SOLA PREGUNTA de opcion multiple (preferentemente) o desarrollo corto.
**Nivel objetivo Bloom:** {target_level}

### FORMATO JSON (devolver solo el JSON, sin texto adicional)

{{
  "numero": {question_number},
  "nivel_bloom": "{target_level}",
  "tipo": "opcion_multiple",
  "enunciado": "[Pregunta clara y especifica, redactada desde la evidencia]",
  "opciones": [
    "A) [opcion plausible]",
    "B) [opcion plausible]",
    "C) [opcion plausible]",
    "D) [opcion correcta pero no obvia]"
  ],
  "_respuesta_correcta": "D",
  "_justificacion": "[Por que D es correcta segun el pasaje, y por que las otras no]",
  "_conceptos_clave": [
    "Concepto X del pasaje que el estudiante debe identificar",
    "Distincion Y que el pasaje establece"
  ],
  "pasaje_fuente": "[Cita textual breve del pasaje que sustenta la pregunta, max 150 chars]",
  "documento_fuente": "[Nombre del documento del que proviene el pasaje]",
  "criterios_evaluacion": {{
    "excelente": "Identifica correctamente y justifica con claridad",
    "insuficiente": "Confunde conceptos fundamentales del pasaje"
  }},
  "recursos_estudio": [
    "Revisar [seccion especifica del documento fuente]"
  ]
}}

REQUISITOS:
- Opciones multiples balanceadas (todas plausibles desde el texto)
- Respuesta correcta no debe ser obvia
- No revelar la respuesta en el enunciado
- pasaje_fuente y documento_fuente obligatorios cuando hay evidencia

GENERA SOLO EL JSON:"""
    
    @staticmethod
    def parse_question_from_llm(llm_response: str) -> Optional[Dict]:
        """
        Extrae el JSON de pregunta de la respuesta del LLM.

        Devuelve:
          - Dict con la pregunta si el parseo fue exitoso
          - {"error": "evidencia_insuficiente"} si el LLM reporto falta de evidencia
          - None si hubo un error de parseo no recuperable
        """
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

            # Propagar evidencia_insuficiente sin modificar
            if question_data.get("error") == "evidencia_insuficiente":
                return question_data

            # Corregir sesgo posicional: el template fija _respuesta_correcta
            # en "D". Se barajan las opciones en el servidor y se reasignan
            # las letras A-D para que la posicion de la respuesta correcta
            # sea aleatoria en cada pregunta.
            question_data = ExamEngine._shuffle_options(question_data)

            return question_data

        except Exception as e:
            print(f"Error parsing question: {e}")
            return None

    @staticmethod
    def _shuffle_options(question_data: Dict) -> Dict:
        """
        Baraja las opciones de opcion multiple reasignando letras A-D.
        Actualiza _respuesta_correcta con la nueva letra de la opcion correcta.
        No modifica preguntas de desarrollo o sin opciones.
        """
        opciones = question_data.get("opciones", [])
        respuesta_correcta = question_data.get("_respuesta_correcta", "").upper().strip()

        if not opciones or not respuesta_correcta:
            return question_data

        # Mapear letra -> texto de opcion original (quitar prefijo "A) " etc.)
        letras = ["A", "B", "C", "D"]
        contenidos = {}
        for op in opciones:
            for letra in letras:
                if op.upper().startswith(f"{letra})") or op.upper().startswith(f"{letra}."):
                    contenidos[letra] = op[2:].strip()
                    break

        if len(contenidos) < 2:
            return question_data

        # Identificar el texto de la opcion correcta antes de barajar
        texto_correcto = contenidos.get(respuesta_correcta)
        if texto_correcto is None:
            return question_data

        # Barajar los textos
        textos = list(contenidos.values())
        random.shuffle(textos)

        # Reasignar letras y encontrar la nueva letra de la correcta
        nuevas_opciones = []
        nueva_letra_correcta = respuesta_correcta  # fallback
        for i, texto in enumerate(textos):
            letra = letras[i]
            nuevas_opciones.append(f"{letra}) {texto}")
            if texto == texto_correcto:
                nueva_letra_correcta = letra

        question_data["opciones"] = nuevas_opciones
        question_data["_respuesta_correcta"] = nueva_letra_correcta
        return question_data
    
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
            cleaned = student_answer.strip().upper() if student_answer else ""
            student_letter = cleaned[0] if cleaned else ""
            is_correct = (student_letter == correct_letter)
        
        # Criterios de evaluación
        criterios = question.get("criterios_evaluacion", {})
        
        # Generar feedback segun resultado.
        # La longitud de la respuesta NO indica calidad: en opcion multiple el
        # estudiante escribe una letra, por lo que len() < 20 siempre y el
        # criterio anterior devolia sistematicamente "bueno" en lugar de
        # "excelente". Se usa directamente el criterio "excelente" cuando es
        # correcta, "insuficiente" cuando no lo es.
        if is_correct:
            nivel = "excelente"
            feedback_base = criterios.get(nivel, "Respuesta correcta")
            
            feedback = f"""### Respuesta Correcta

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
            
            feedback = f"""### Oportunidad de Aprendizaje

{feedback_base}

**Áreas de reflexión:**
No te preocupes, el error es parte del aprendizaje. Esta pregunta toca conceptos importantes.

**Te recomiendo:**
"""
            for recurso in question.get("recursos_estudio", []):
                feedback += f"- {recurso}\n"
            
            # _conceptos_clave no se incluye en el feedback: su contenido
            # (p.ej. "Debe identificar X") puede revelar la respuesta correcta
            # cuando el estudiante falla. Se usa en cambio recursos_estudio,
            # que no contiene la respuesta.
        
        return {
            "is_correct": is_correct,
            # outcome_label: "excelente"/"insuficiente" son etiquetas de
            # correccion, NO niveles SOLO. El campo "nivel" se conserva por
            # compatibilidad con main.py pero NO debe escribirse en
            # exam_responses.solo_level (ver main.py P0.2).
            "outcome_label": "excelente" if is_correct else "insuficiente",
            "nivel": "excelente" if is_correct else "insuficiente",
            "feedback": feedback,
            "recursos_recomendados": question.get("recursos_estudio", []),
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
            nivel_global = "Excelente comprension"
            descripcion = "Demuestras dominio sólido de los conceptos estudiados. Has alcanzado los objetivos de aprendizaje."
        elif correct_count >= total_questions * 0.7:
            nivel_global = "Buena comprension"
            descripcion = "Tienes una base sólida. Con un poco más de práctica alcanzarás el dominio completo."
        elif correct_count >= total_questions * 0.5:
            nivel_global = "Comprension en desarrollo"
            descripcion = "Estás construyendo tu conocimiento. Dedica tiempo a repasar los conceptos fundamentales."
        else:
            nivel_global = "Iniciando el aprendizaje"
            descripcion = "Estás en las etapas iniciales. No te desanimes, todos comenzamos aquí. Enfócate en los conceptos básicos."
        
        summary = f"""# Resumen del Examen Formativo

## {nivel_global}

{descripcion}

---

## Resultados

**Preguntas respondidas:** {total_questions}
**Respuestas correctas:** {correct_count}

### Distribución por Nivel Bloom
"""
        
        for nivel, count in bloom_distribution.items():
            summary += f"- **{nivel.title()}:** {count} pregunta(s)\n"
        
        summary += f"""
---

## Revision Detallada

"""
        for i, qa in enumerate(questions_and_answers, 1):
            q = qa.get("question", {})
            ev = qa.get("evaluation", {})
            is_correct = ev.get("is_correct", False)
            icon = "✅" if is_correct else "❌"
            enunciado = q.get("enunciado", "")
            correct_letter = q.get("_respuesta_correcta", "")
            opciones = q.get("opciones", [])

            summary += f"### {'Correcta' if is_correct else 'Incorrecta'}: Pregunta {i} — {q.get('nivel_bloom','').title()}\n\n"
            summary += f"{enunciado}\n\n"
            if opciones:
                for op in opciones:
                    summary += f"{op}\n"
                summary += "\n"
            summary += f"**Tu respuesta:** {qa.get('answer','')}\n\n"
            # La respuesta correcta NO se revela en el resumen para preservar
            # el valor de uso de las preguntas en exámenes futuros.
            # Si en el futuro se decide mostrarla, agregar aqui.
            summary += f"**Retroalimentacion:** {ev.get('feedback','').splitlines()[1] if ev.get('feedback') else ''}\n\n---\n\n"

        summary += f"""
## Temas cubiertos

"""
        for topic in topics_covered[:5]:
            summary += f"- {topic.replace('_', ' ').title()}\n"

        # Fortalezas y áreas de mejora
        summary += """
---

## Fortalezas Observadas

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

## Plan de Accion

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

## Proximos Pasos

1. **Revisa los recursos sugeridos** en cada pregunta
2. **Practica** con ejercicios adicionales
3. **Consulta** cuando tengas dudas
4. **Vuelve a intentar** cuando te sientas preparado

---

**Nota:** Este examen es formativo, no sumativo. Su objetivo es ayudarte a identificar qué sabes y qué necesitas reforzar. El aprendizaje es un proceso continuo.

¿Deseas comenzar una nueva conversación o profundizar en algún tema específico?
"""
        
        return summary
