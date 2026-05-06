# Rediseño del Flujo de Trabajo - Sistema RAG v2

## Flujo Propuesto vs. Implementación Actual

### 📋 Flujo Deseado

1. **Consultas de Conceptos (RAG Puro)**
   - Los alumnos consultan conceptos
   - El RAG retorna **3 resultados diferentes de 3 fuentes distintas** (si existen)
   - **Sin interpretaciones**, solo traducciones fieles
   - Presentación de las 3 opciones más cercanas

2. **Continuación de Preguntas**
   - Todas las preguntas son respondidas por RAG
   - Sin evaluación ni análisis cualitativo en esta fase

3. **Oferta de Evaluación**
   - Después de varias preguntas (umbral configurable)
   - Sistema pregunta: "¿Deseas hacer una evaluación?"

4. **Evaluación con LLM Generativo**
   - Si acepta: LLM genera 5 preguntas de opción múltiple
   - Basadas en las búsquedas del usuario
   - **No se muestra calificación numérica**

5. **Análisis con Bloom + SOLO**
   - Las respuestas se analizan cualitativamente
   - Se da retroalimentación sobre las respuestas
   - Se genera estrategia personalizada de estudio

6. **Persistencia Total**
   - Todas las consultas de conceptos
   - Preguntas generadas
   - Respuestas de usuarios
   - Análisis (Bloom/SOLO)
   - Estrategias sugeridas
   - Por usuario y sesión

7. **Análisis Avanzado**
   - Análisis de sentimiento sobre respuestas
   - Análisis de estrategias sugeridas
   - Métricas por usuario/sesión

---

## 🔍 Análisis de la Implementación Actual

### ✅ Lo que YA está implementado:

1. **Sistema de exámenes conversacional** (exam_engine.py)
   - Genera preguntas una por una
   - Evalúa respuestas con Bloom + SOLO
   - Proporciona feedback sin revelar calificación
   - Genera resumen final con plan de mejora

2. **Base de datos completa** (database.py)
   - Tablas: Exam, ExamResponse, ExamResult
   - Almacena evaluaciones, niveles Bloom/SOLO
   - Campos para análisis de sentimiento

3. **Analytics Engine** (analytics_engine.py)
   - Análisis de sentimiento
   - Detección de tópicos
   - Evaluación de complejidad

4. **Qualitative Evaluator** (qualitative_evaluator.py)
   - Clasificación Bloom
   - Evaluación SOLO
   - Feedback constructivo

### ❌ Lo que NECESITA modificación:

1. **RAG Engine - Respuestas Múltiples**
   - Actualmente: Combina resultados de múltiples fuentes en UNA respuesta interpretada
   - Necesario: Retornar 3 resultados SEPARADOS de 3 fuentes DISTINTAS

2. **Flujo de Consulta - Sin Evaluación Inicial**
   - Actualmente: SIEMPRE agrega evaluación cualitativa (Bloom/SOLO) en consultas RAG
   - Necesario: Solo RAG puro, SIN análisis en fase de consultas

3. **Umbral de Oferta de Examen**
   - Actualmente: Se ofrece después de 3 consultas y 2 temas
   - Necesario: Configurable y más claro en la presentación

4. **Número de Preguntas de Examen**
   - Actualmente: 3-5 preguntas (variable)
   - Necesario: Exactamente 5 preguntas de opción múltiple

5. **Análisis de Sentimiento en Respuestas**
   - Actualmente: Solo en queries del usuario
   - Necesario: También análisis de sentimiento en respuestas de examen

---

## 🛠️ Plan de Implementación

### Fase 1: Modificar RAG Engine

**Archivo:** `app/rag_engine.py`

**Cambios:**

```python
async def query_multi_source(
    self, 
    query: str, 
    sources_count: int = 3,
    chunks_per_source: int = 1
) -> Dict:
    """
    Retorna resultados SEPARADOS de múltiples fuentes
    
    Returns:
    {
        "results": [
            {
                "source": "Libro A",
                "content": "...",
                "rank": 1
            },
            {
                "source": "Libro B", 
                "content": "...",
                "rank": 2
            },
            {
                "source": "Libro C",
                "content": "...",
                "rank": 3
            }
        ]
    }
    """
```

**Razón:** Presentar opciones separadas sin interpretación

### Fase 2: Modificar Endpoint Principal

**Archivo:** `app/main.py`

**Cambios en `/query` endpoint:**

1. **Eliminar evaluación Bloom/SOLO automática** en consultas RAG normales
2. **Usar nuevo método** `query_multi_source()`
3. **Formato de respuesta:**

```python
# Antes (líneas 562-563)
enhanced_answer = f"{result['answer']}\n\n---\n\n### 📊 Evaluación\n\n"
enhanced_answer += qualitative_feedback["feedback_constructivo"]

# Después
# Solo retornar los 3 resultados separados, SIN evaluación
```

4. **Agregar contador de consultas** para ofrecer examen

### Fase 3: Modificar Sistema de Exámenes

**Archivo:** `app/exam_engine.py`

**Cambios:**

1. **Fijar número de preguntas a 5** (línea 295 en main.py)

```python
# Antes
total_questions = min(5, max(3, len(topics)))

# Después
total_questions = 5  # SIEMPRE 5 preguntas
```

2. **Mejorar oferta de examen** con mensaje más claro

### Fase 4: Agregar Análisis de Sentimiento en Respuestas

**Archivo:** `app/main.py`

**En evaluación de respuestas de examen (línea 383-396):**

```python
# Agregar análisis de sentimiento
sentiment = analytics_engine.analyze_sentiment(query_text)

exam_response = ExamResponse(
    exam_id=active_exam.id,
    user_id=current_user.id,
    question_number=current_q,
    student_answer=query_text,
    bloom_level=current_question.get("nivel_bloom", ""),
    solo_level=evaluation.get("nivel", ""),
    evaluation_data=json.dumps(evaluation),
    sentiment_score=sentiment["score"],  # NUEVO
    sentiment_label=sentiment["label"]   # NUEVO
)
```

**Nota:** Requiere agregar campos a tabla `exam_responses`

### Fase 5: Actualizar Base de Datos

**Archivo:** `app/database.py`

**Modificar ExamResponse:**

```python
class ExamResponse(Base):
    # ... campos existentes ...
    
    # NUEVOS CAMPOS
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)
```

### Fase 6: Crear Endpoint de Analytics

**Nuevo endpoint en `app/main.py`:**

```python
@app.get("/analytics/user/{user_id}")
async def get_user_analytics(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Análisis completo del usuario:
    - Consultas realizadas
    - Exámenes tomados
    - Distribución Bloom/SOLO
    - Análisis de sentimiento
    - Estrategias sugeridas
    - Progreso temporal
    """
```

---

## 📊 Estructura de Datos Mejorada

### Consultas RAG

```json
{
  "query": "¿Qué es un orbital atómico?",
  "response_type": "multi_source",
  "results": [
    {
      "rank": 1,
      "source": "Bransden-Joachain Physics of Atoms and Molecules",
      "content": "An atomic orbital is a mathematical function describing the wave-like behavior of either one electron or a pair of electrons in an atom...",
      "relevance_score": 0.95
    },
    {
      "rank": 2,
      "source": "Estructura Atómica - Garritz",
      "content": "Un orbital atómico es una región del espacio alrededor del núcleo donde existe una alta probabilidad de encontrar un electrón...",
      "relevance_score": 0.89
    },
    {
      "rank": 3,
      "source": "Inorganic Chemistry - Huheey",
      "content": "Orbitals are regions in space where electrons are most likely to be found. Each orbital has a characteristic shape and energy...",
      "relevance_score": 0.84
    }
  ],
  "query_count": 5,
  "should_offer_exam": false
}
```

### Oferta de Examen

```json
{
  "message": "¡Excelente progreso! Has realizado 8 consultas sobre 4 temas diferentes.",
  "should_offer_exam": true,
  "topics_covered": ["orbitales atómicos", "configuración electrónica", "números cuánticos", "spin electrónico"],
  "queries_count": 8,
  "suggestion": "¿Te gustaría hacer una evaluación formativa para consolidar lo aprendido?"
}
```

### Resultado de Examen

```json
{
  "exam_id": 123,
  "total_questions": 5,
  "responses": [
    {
      "question_number": 1,
      "bloom_level": "comprender",
      "solo_level": "multiestructural",
      "sentiment": {
        "score": 0.6,
        "label": "positive"
      },
      "feedback": "...",
      "improvement_suggestions": ["..."]
    }
  ],
  "overall_analysis": {
    "predominant_bloom": "aplicar",
    "predominant_solo": "relacional",
    "average_sentiment": 0.45,
    "strengths": ["..."],
    "improvement_areas": ["..."],
    "personalized_strategy": {
      "immediate_actions": ["..."],
      "study_resources": ["..."],
      "practice_exercises": ["..."],
      "estimated_time": "1-2 semanas"
    }
  }
}
```

---

## 🚀 Orden de Implementación

1. ✅ **[YA HECHO]** Base de datos con Bloom + SOLO
2. ✅ **[YA HECHO]** Sistema de exámenes conversacional
3. ✅ **[YA HECHO]** Analytics y evaluación cualitativa
4. 🔄 **[PENDIENTE]** Modificar RAG para respuestas múltiples
5. 🔄 **[PENDIENTE]** Eliminar evaluación en consultas normales
6. 🔄 **[PENDIENTE]** Fijar exámenes a 5 preguntas
7. 🔄 **[PENDIENTE]** Agregar sentimiento a respuestas de examen
8. 🔄 **[PENDIENTE]** Actualizar esquema de base de datos
9. 🔄 **[PENDIENTE]** Crear endpoint de analytics completo
10. 🔄 **[PENDIENTE]** Actualizar frontend para mostrar 3 resultados

---

## 📝 Notas de Implementación

### Ventajas del Sistema Actual

- ✅ Ya tiene toda la infraestructura de Bloom + SOLO
- ✅ Sistema de exámenes robusto y bien diseñado
- ✅ Base de datos preparada
- ✅ Analytics engine funcionando

### Cambios Mínimos Necesarios

- 🔧 RAG Engine: agregar método para resultados separados
- 🔧 Main.py: remover evaluación automática
- 🔧 Main.py: usar nuevo formato de respuesta
- 🔧 Database: agregar 2 campos a ExamResponse
- 🔧 Frontend: mostrar 3 resultados en lugar de 1

### Tiempo Estimado

- Modificaciones backend: **2-3 horas**
- Actualizaciones de base de datos: **30 minutos**
- Modificaciones frontend: **1-2 horas**
- Pruebas y ajustes: **1 hora**

**Total: ~5-7 horas de trabajo**

---

## 🎯 Resultado Final

El sistema tendrá:

1. **Fase de Consulta**: RAG puro con 3 resultados de fuentes diferentes
2. **Fase de Evaluación**: Sistema de exámenes con 5 preguntas
3. **Fase de Análisis**: Bloom + SOLO + Sentimiento + Estrategia personalizada
4. **Analytics Completo**: Por usuario, sesión, con métricas detalladas
5. **Sin calificaciones numéricas**: Solo feedback cualitativo
6. **Persistencia total**: Todo guardado en base de datos local

Este diseño es **pedagógicamente sólido** y permite **análisis profundo** del aprendizaje estudiantil.