# Plan de Implementación Detallado - Rediseño de Flujo de Trabajo

## 📋 Resumen Ejecutivo

**Objetivo**: Modificar el sistema RAG v2 para implementar el flujo de trabajo deseado donde:
1. RAG muestra 3 resultados separados de fuentes distintas (sin interpretación)
2. No hay evaluación Bloom/SOLO automática en consultas normales
3. Exámenes siempre tienen 5 preguntas
4. Análisis de sentimiento se aplica también a respuestas de examen
5. Todo se persiste en base de datos

**Estado Actual**: ~70% implementado, necesita ajustes específicos

**Tiempo Estimado**: 5-7 horas en 8 pasos incrementales

---

## 🗺️ Roadmap de Implementación

```
PASO 1: Plan Detallado [15 min] ✅
   └── Crear este documento con plan completo

PASO 2: RAG Multi-Source [2h]
   ├── Crear método query_multi_source() en RAGEngine
   ├── Mantener método original para compatibilidad
   └── Probar con consultas de ejemplo

PASO 3: Actualizar Base de Datos [30 min]
   ├── Agregar campos sentiment a ExamResponse
   ├── Crear migración
   └── Verificar integridad

PASO 4: Modificar Endpoint /query [1.5h]
   ├── Eliminar evaluación automática Bloom/SOLO
   ├── Usar query_multi_source()
   ├── Nuevo formato de respuesta
   └── Probar queries normales

PASO 5: Fijar Exámenes a 5 Preguntas [15 min]
   ├── Cambiar lógica en main.py línea 295
   └── Probar generación de examen

PASO 6: Sentimiento en Respuestas de Examen [45 min]
   ├── Agregar análisis en evaluación de respuestas
   ├── Guardar en ExamResponse
   └── Probar flujo completo de examen

PASO 7: Actualizar Frontend [1.5h]
   ├── Modificar componente de mensajes
   ├── Mostrar 3 resultados separados
   ├── Actualizar estilos
   └── Probar interfaz

PASO 8: Testing Integral [1h]
   ├── Flujo completo de usuario
   ├── Verificar persistencia en DB
   └── Validar analytics

PASO 9: Documentación [30 min]
   ├── Actualizar README
   └── Crear guía de usuario
```

**Total: ~7.5 horas** (redondeado a 8h para buffer)

---

## 📝 PASO 1: Plan Detallado ✅

**Duración**: 15 minutos  
**Estado**: ✅ COMPLETADO

**Resultado**: Este documento

---

## 🔧 PASO 2: Implementar RAG Multi-Source

**Duración estimada**: 2 horas  
**Archivo principal**: `app/rag_engine.py`  
**Prioridad**: ALTA (es el cambio más importante)

### 2.1 Crear nuevo método `query_multi_source()`

**Ubicación**: Agregar después de la línea 114 en `rag_engine.py`

**Código a agregar**: Ver sección completa en documento

### 2.2 Criterios de éxito

- [ ] Método `query_multi_source()` creado
- [ ] Retorna exactamente 3 resultados (o menos si no hay suficientes fuentes)
- [ ] Cada resultado es de una fuente DISTINTA
- [ ] No hay interpretación, solo contenido directo del chunk
- [ ] Tiempo de respuesta < 5 segundos

---

## 🗄️ PASO 3: Actualizar Base de Datos

**Duración estimada**: 30 minutos  
**Archivo principal**: `app/database.py`  
**Prioridad**: MEDIA (necesario antes del paso 6)

### 3.1 Modificar tabla ExamResponse

Agregar campos `sentiment_score` y `sentiment_label`

### 3.2 Crear script de migración

### 3.3 Criterios de éxito

- [ ] Campos agregados a `ExamResponse`
- [ ] Script de migración creado
- [ ] Migración ejecutada sin errores
- [ ] Base de datos actualizada

---

## 🔄 PASO 4: Modificar Endpoint /query

**Duración estimada**: 1.5 horas  
**Archivo principal**: `app/main.py`  
**Prioridad**: ALTA

### 4.1 Cambios principales

- Eliminar evaluación Bloom/SOLO automática
- Usar `query_multi_source()`
- Nuevo formato de respuesta
- Agregar campo `should_offer_exam`

### 4.2 Criterios de éxito

- [ ] Código modificado
- [ ] Respuestas usan nuevo método
- [ ] NO se agrega evaluación automática
- [ ] Campo `should_offer_exam` funciona

---

## 🎯 PASO 5: Fijar Exámenes a 5 Preguntas

**Duración estimada**: 15 minutos  
**Archivo**: `app/main.py` línea 295  
**Cambio**: `total_questions = 5`

---

## 💭 PASO 6: Sentimiento en Respuestas de Examen

**Duración estimada**: 45 minutos  
**Cambio**: Agregar análisis de sentimiento al guardar ExamResponse

---

## 🎨 PASO 7: Actualizar Frontend

**Duración estimada**: 1.5 horas  
**Archivo**: `frontend/index.html`

### Cambios:
- Función `renderMultiSourceResults()`
- Estilos CSS para 3 tarjetas
- Modificar `addMessage()` y `sendMessage()`

---

## ✅ PASO 8: Testing Integral

**Duración estimada**: 1 hora

### Test Cases:
1. Flujo de consultas RAG (3 resultados)
2. Oferta de examen (después de 8 consultas)
3. Examen de 5 preguntas
4. Sentimiento en respuestas
5. Frontend multi-source

---

## 📚 PASO 9: Documentación

**Duración estimada**: 30 minutos

- Actualizar README
- Crear USER_GUIDE.md

---

## 🎯 Criterios de Éxito Global

✅ **Funcionalidad**:
- [ ] Consultas RAG muestran 3 resultados separados
- [ ] NO hay evaluación automática
- [ ] Exámenes siempre 5 preguntas
- [ ] Sentimiento en exámenes
- [ ] Oferta de examen funciona

✅ **Persistencia**:
- [ ] Todo en base de datos
- [ ] Campos nuevos funcionan
- [ ] Sin pérdida de datos

✅ **UX**:
- [ ] Frontend muestra 3 resultados
- [ ] Diseño responsive
- [ ] Sin errores

✅ **Performance**:
- [ ] Queries < 5 segundos
- [ ] Sin errores en logs

---

## 📞 ¿Listo para comenzar?

**PASO 2** (RAG Multi-Source) es el siguiente.

¿Procedo con la implementación?