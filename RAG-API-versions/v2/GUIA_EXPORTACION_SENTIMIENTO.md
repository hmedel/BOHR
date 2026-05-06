# Guía Rápida: Exportación y Análisis de Sentimiento

## 📋 Resumen

Este sistema te permite exportar y analizar todos los datos de sentimiento, exámenes y conversaciones de la base de datos RAG v2.

## 🚀 Uso Rápido

### 1. Exportar Base de Datos Completa

```bash
cd /home/medel/BOHR/RAG-API-versions/v2
python export_db.py
```

**Resultado**: Crea un directorio `exports/export_YYYYMMDD_HHMMSS/` con todos los datos.

### 2. Analizar Sentimiento con Visualizaciones

```bash
python analyze_sentiment.py
```

**Resultado**: Genera gráficos y reportes de análisis en el directorio de exportación más reciente.

### 3. Exportar Datos de Usuario Específico

```bash
# Por ID de usuario
python export_db.py --user-id 1

# Por conversación específica
python export_db.py --conversation-id 5

# Por examen específico
python export_db.py --exam-id 1
```

## 📊 Archivos Generados

### Exportación Completa

Cada exportación crea **14 archivos**:

#### Datos Principales (CSV/JSON)
- `users.csv` - Lista de usuarios (29 usuarios)
- `conversations.csv` - Conversaciones (20 conversaciones)
- `messages_sentiment.csv/json` - Mensajes con análisis de sentimiento (144 mensajes)
- `exam_responses.csv/json` - Respuestas de exámenes (6 respuestas)
- `exams.csv` y `exams_full.json` - Exámenes generados (2 exámenes)
- `exam_results.json` - Resultados finales (1 resultado)
- `student_progress.json` - Progreso por estudiante (7 estudiantes)

#### Resúmenes
- `sentiment_summary_messages.csv` - Resumen de sentimiento en mensajes
- `sentiment_summary_exams.csv` - Resumen de sentimiento en exámenes
- `export_report.txt` - Reporte ejecutivo

### Análisis de Sentimiento

El análisis genera:
- `sentiment_analysis_summary.txt` - Reporte de análisis
- `analysis_plots/messages_sentiment_analysis.png` - Visualizaciones de mensajes
- `analysis_plots/exams_sentiment_analysis.png` - Visualizaciones de exámenes

## 📈 Datos Incluidos en Análisis de Sentimiento

### Para Mensajes
```python
{
    "sentiment_score": float,      # -1.0 (negativo) a 1.0 (positivo)
    "sentiment_label": str,        # "positive", "neutral", "negative"
    "query_complexity": str,       # "basic", "intermediate", "advanced"
    "topics": str,                 # Temas detectados (JSON)
    "bloom_level": str,            # Nivel taxonomía Bloom
    "solo_level": str,             # Nivel taxonomía SOLO
    "qualitative_feedback": str    # Retroalimentación
}
```

### Para Respuestas de Examen
```python
{
    "student_answer": str,
    "bloom_level": str,            # "recordar", "comprender", "aplicar", etc.
    "solo_level": str,             # "prestructural", "unistructural", etc.
    "sentiment_score": float,
    "sentiment_label": str,
    "evaluation_data": dict        # Datos detallados (JSON)
}
```

## 📊 Estadísticas Actuales (Última Exportación)

```
✓ Usuarios registrados: 29
✓ Conversaciones: 20
✓ Mensajes totales: 144
✓ Exámenes generados: 2
✓ Respuestas de examen: 6
✓ Resultados de examen: 1
✓ Estudiantes con progreso: 7

Análisis de Sentimiento:
- Mensajes analizados: 72
- Respuestas de examen: 6
- Sentimiento promedio: neutral (0.000)
- Distribución: 100% neutral
```

## 🔧 Análisis Personalizado con Pandas

### Ejemplo 1: Cargar y Analizar Mensajes

```python
import pandas as pd
import json

# Cargar mensajes
df = pd.read_csv('exports/export_YYYYMMDD_HHMMSS/messages_sentiment.csv')

# Filtrar mensajes de usuario
df_user = df[df['role'] == 'user']

# Análisis por usuario
user_analysis = df_user.groupby('username').agg({
    'sentiment_score': 'mean',
    'query_complexity': lambda x: x.value_counts().to_dict(),
    'id': 'count'
}).rename(columns={'id': 'num_messages'})

print(user_analysis)

# Mensajes con sentimiento negativo
negative = df_user[df_user['sentiment_label'] == 'negative']
print(f"Mensajes negativos: {len(negative)}")
```

### Ejemplo 2: Analizar Exámenes

```python
# Cargar respuestas
df_responses = pd.read_csv('exports/export_YYYYMMDD_HHMMSS/exam_responses.csv')

# Distribución de niveles Bloom
bloom_dist = df_responses['bloom_level'].value_counts()
print("Distribución Bloom:")
print(bloom_dist)

# Distribución SOLO
solo_dist = df_responses['solo_level'].value_counts()
print("\nDistribución SOLO:")
print(solo_dist)

# Correlación sentimiento-nivel
correlation = df_responses.groupby(['bloom_level', 'sentiment_label']).size()
print("\nCorrelación:")
print(correlation)
```

### Ejemplo 3: Progreso de Estudiantes

```python
# Cargar progreso
df_progress = pd.read_json('exports/export_YYYYMMDD_HHMMSS/student_progress.json')

# Top 10 estudiantes más activos
top_students = df_progress.nlargest(10, 'total_queries')[
    ['username', 'total_queries', 'avg_sentiment', 'satisfaction_rate']
]
print(top_students)

# Promedio de satisfacción
avg_satisfaction = df_progress['satisfaction_rate'].mean()
print(f"Satisfacción promedio: {avg_satisfaction:.2%}")
```

## 🎯 Casos de Uso

### 1. Identificar Estudiantes con Dificultades
```python
# Buscar estudiantes con sentimiento negativo consistente
problematic = df_progress[df_progress['avg_sentiment'] < -0.2]
```

### 2. Detectar Temas Difíciles
```python
# Mensajes con alta complejidad y bajo sentimiento
difficult_topics = df_user[
    (df_user['query_complexity'] == 'advanced') &
    (df_user['sentiment_score'] < 0)
]['topics'].value_counts()
```

### 3. Evaluar Efectividad de Exámenes
```python
# Analizar distribución de niveles cognitivos
exam_effectiveness = df_responses.groupby('bloom_level').agg({
    'solo_level': lambda x: x.value_counts().to_dict(),
    'sentiment_score': 'mean'
})
```

### 4. Análisis Temporal
```python
# Evolución del sentimiento en el tiempo
df['created_at'] = pd.to_datetime(df['created_at'])
df_sorted = df.sort_values('created_at')
df_sorted['rolling_sentiment'] = df_sorted['sentiment_score'].rolling(10).mean()

# Graficar tendencia
import matplotlib.pyplot as plt
plt.plot(df_sorted['created_at'], df_sorted['rolling_sentiment'])
plt.xlabel('Fecha')
plt.ylabel('Sentimiento (promedio móvil)')
plt.title('Evolución del Sentimiento')
plt.show()
```

## ⚠️ Notas Importantes

### Observación: Sentimiento Neutral Predominante

Los datos actuales muestran **100% sentimiento neutral** (score = 0.0). Esto puede indicar:

1. **El análisis de sentimiento no está activo**: Verificar que `analytics_engine.py` esté calculando sentimientos
2. **Datos no procesados**: Los mensajes pueden no haber pasado por el motor de analytics
3. **Configuración pendiente**: Verificar que el sistema esté usando el motor de análisis

#### Solución: Activar Análisis de Sentimiento

Verificar en `app/main.py` que el análisis de sentimiento esté activo:

```python
# Debería estar presente en el flujo de consultas
analytics_result = analytics_engine.analyze_query(user_message)
```

### Privacidad y Seguridad

- ⚠️ Los archivos exportados contienen datos de usuarios
- 🔒 No compartir archivos CSV/JSON públicamente
- 🗑️ Eliminar exportaciones antiguas: `rm -rf exports/export_*`
- 📁 Mantener backups seguros

### Performance

- Exportación completa: ~1-2 segundos
- Análisis con visualizaciones: ~2-3 segundos
- Archivos totales generados: ~600 KB

## 📚 Recursos Adicionales

- **Documentación completa**: `exports/README.md`
- **Estructura de BD**: `app/database.py`
- **Motor de analytics**: `app/analytics_engine.py`
- **Evaluador cualitativo**: `app/qualitative_evaluator.py`

## 🆘 Soporte

### Problemas Comunes

**Error: No module named 'pandas'**
```bash
pip install pandas matplotlib seaborn
```

**Error: No se encuentra la base de datos**
```bash
# Verificar que exista
ls -lh data/rag_system.db

# Debe estar en: /home/medel/BOHR/RAG-API-versions/v2/data/rag_system.db
```

**Exportación vacía**
```bash
# Verificar que hay datos
sqlite3 data/rag_system.db "SELECT COUNT(*) FROM messages;"
```

## 🔄 Flujo de Trabajo Recomendado

1. **Exportar periódicamente** (semanal/mensual):
   ```bash
   python export_db.py
   ```

2. **Analizar después de cada exportación**:
   ```bash
   python analyze_sentiment.py
   ```

3. **Revisar reportes y gráficos** en `exports/export_*/`

4. **Análisis personalizado** con Pandas según necesidades

5. **Archivar exportaciones importantes**:
   ```bash
   tar -czf export_backup_$(date +%Y%m%d).tar.gz exports/export_*
   ```

---

**Última actualización**: 2025-12-08
**Versión**: v2
**Ubicación**: `/home/medel/BOHR/RAG-API-versions/v2/`
