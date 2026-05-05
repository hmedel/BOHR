# BOHR RAG v2 - Asistente de Estructura de la Materia

Sistema de tutoría inteligente basado en Retrieval-Augmented Generation (RAG) para la materia "Estructura de la Materia" en la Facultad de Estudios Superiores Cuautitlan (FESC-UNAM).

## Descripcion

BOHR RAG v2 es un chatbot educativo que:

- Responde preguntas sobre fisica atomica, quimica cuantica y estructura de la materia usando 7 libros de texto indexados
- Renderiza ecuaciones matematicas en LaTeX (KaTeX)
- Ofrece examenes formativos conversacionales (5 preguntas, opcion multiple)
- Evalua respuestas usando taxonomia de Bloom y modelo SOLO
- Analiza sentimiento y complejidad de las consultas
- Mantiene historial persistente de conversaciones por usuario

## Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | FastAPI + Uvicorn (Python 3.11) |
| Frontend | HTML/CSS/JS vanilla (SPA) |
| LLM | DeepSeek API (deepseek-chat) |
| Embeddings | Ollama (nomic-embed-text, local) |
| Vector DB | ChromaDB (persistente, ~11,800 chunks) |
| Base de datos | SQLite (usuarios, conversaciones, examenes) |
| Autenticacion | JWT (HS256, 7 dias) + SHA256 passwords |
| Matematicas | KaTeX 0.16.9 (frontend) |
| Markdown | Marked.js + Highlight.js |
| Tunnel | Cloudflare Tunnel (HTTPS publico) |

## Inicio Rapido

### Requisitos

- Python 3.11+ (via Conda: `bohrenv`)
- Ollama con modelo `nomic-embed-text`
- Clave API de DeepSeek
- Cloudflare Tunnel (para acceso publico)

### Instalacion

```bash
# Clonar y entrar al directorio
cd /home/medel/BOHR/RAG-API-versions/v2

# Crear entorno conda
conda create -n bohrenv python=3.11
conda activate bohrenv

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus claves API

# Verificar Ollama
curl http://localhost:11434/api/tags
# Debe mostrar nomic-embed-text

# Indexar documentos (primera vez)
./load_books.sh
```

### Ejecucion

```bash
# Activar entorno
conda activate bohrenv

# Iniciar backend (12 workers)
nohup python -m uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 --workers 12 --log-level info \
  > logs/backend_production.log 2>&1 &
disown

# Iniciar frontend
cd frontend && nohup python -m http.server 9000 > frontend.log 2>&1 &

# Verificar
curl http://localhost:8000/health
# {"status":"healthy","version":"2.6"}
```

### Acceso

- **Local**: http://localhost:9000
- **Red interna**: http://132.248.102.133:9000
- **Publico**: https://chat.bohrbot.space

## Arquitectura

```
                    ┌──────────────────────────┐
                    │   Cloudflare Tunnel       │
                    │   chat.bohrbot.space       │
                    │   api.bohrbot.space        │
                    └────────┬─────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   │
┌─────────────────┐ ┌────────────────┐           │
│ Frontend :9000  │ │ Backend :8000  │           │
│ index.html      │ │ FastAPI        │           │
│ Marked.js       │ │                │           │
│ KaTeX 0.16.9    │ │ ┌────────────┐ │           │
│ Highlight.js    │ │ │ RAG Engine │ │           │
└─────────────────┘ │ │ (LangChain)│ │           │
                    │ └──────┬─────┘ │           │
                    │ ┌──────┼──────┐│           │
                    │ │Exam  │Analyt││           │
                    │ │Engine│Engine ││           │
                    │ └──────┼──────┘│           │
                    │ ┌──────┼──────┐│           │
                    │ │ Auth │Qualit││           │
                    │ │(JWT) │Eval  ││           │
                    │ └──────┴──────┘│           │
                    └───┬────┬───┬───┘           │
                        │    │   │               │
                ┌───────┘    │   └──────┐        │
                ▼            ▼          ▼        │
          ┌──────────┐ ┌──────────┐ ┌────────┐   │
          │ Ollama   │ │ ChromaDB │ │ SQLite │   │
          │ :11434   │ │ (local)  │ │ (local)│   │
          │ nomic-   │ │ 7 libros │ │ 8 tablas│  │
          │ embed    │ │ 11.8K    │ │        │   │
          └──────────┘ │ chunks   │ └────────┘   │
                       └──────────┘              │
                ┌────────────────────────────────┘
                ▼
          ┌──────────┐
          │ DeepSeek │
          │ API      │
          │ (LLM)    │
          └──────────┘
```

## Flujo de una Consulta RAG

1. Usuario envia pregunta via frontend
2. Backend verifica JWT y extrae usuario
3. Analisis: sentimiento (TextBlob), temas, complejidad
4. Guarda mensaje del usuario en SQLite
5. Embedding de la pregunta via Ollama (nomic-embed-text)
6. Busqueda en ChromaDB: 7 documentos x 10 chunks cada uno
7. Ranking por relevancia, seleccion de top 3 fuentes (30 chunks)
8. Envio a DeepSeek: contexto (~9K tokens) + prompt de sintesis + pregunta
9. Post-procesamiento: correccion de LaTeX, limpieza de Unicode math
10. Guarda respuesta y actualiza progreso del estudiante
11. Frontend: protege LaTeX con placeholders, renderiza Markdown, restaura LaTeX, aplica KaTeX

## Flujo de un Examen

```
"Quiero un examen"
    │
    ├─ <3 consultas o <2 temas → "Aun no estas listo"
    │
    └─ Listo → "¿Deseas comenzar? Responde 'Si, comenzar'"
                    │
                    └─ "Si, comenzar"
                        │
                        ├─ Genera Q1 (nivel: comprender)
                        │   └─ Estudiante responde
                        │       └─ Feedback inmediato + Q2 (nivel: aplicar)
                        │           └─ ... hasta Q5 (nivel: analizar)
                        │               └─ Resumen final:
                        │                   - Nivel global
                        │                   - Distribucion Bloom
                        │                   - Fortalezas
                        │                   - Plan de accion
                        │
                        └─ "Cancelar examen" → Cancela y vuelve a modo RAG
```

## Documentos Indexados

| Libro | Chunks | Idioma |
|---|---|---|
| Inorganic Chemistry (Huheey) | 2,734 | EN |
| Introduction to Structure of Matter | 2,041 | EN |
| Old Quantum Theory & Early QM | 1,898 | EN |
| Atoms, Molecules and Photons | 1,667 | EN |
| Estructura Atomica (Cruz/Garritz) | 1,522 | ES |
| Bransden & Joachain - Physics of Atoms | 1,454 | EN |
| Atomic Spectra & Atomic Structure | 496 | EN |
| **Total** | **11,812** | |

## Estructura de Directorios

```
v2/
├── app/                          # Backend Python
│   ├── main.py                   # FastAPI app (695 lineas)
│   ├── rag_engine.py             # RAG pipeline (~600 lineas)
│   ├── exam_engine.py            # Sistema de examenes (372 lineas)
│   ├── analytics_engine.py       # Analisis de sentimiento (125 lineas)
│   ├── qualitative_evaluator.py  # Bloom/SOLO evaluacion (297 lineas)
│   ├── database.py               # Modelos SQLAlchemy (178 lineas)
│   ├── auth.py                   # Autenticacion JWT (50 lineas)
│   └── config.py                 # Configuracion (23 lineas)
├── frontend/                     # Frontend estatico
│   ├── index.html                # SPA completa (~1100 lineas)
│   ├── config.js                 # Deteccion de entorno
│   ├── bohr.png                  # Favicon
│   ├── logo-FESC.png             # Logo FESC
│   └── pumas.png                 # Avatar del asistente
├── data/                         # Datos persistentes
│   ├── rag_system.db             # Base de datos SQLite
│   ├── chroma/                   # Vector store ChromaDB
│   ├── uploads/                  # Documentos markdown
│   └── backups/                  # Respaldos historicos
├── logs/                         # Logs de produccion
├── .env                          # Variables de entorno
├── requirements.txt              # Dependencias Python
├── Dockerfile                    # Imagen Docker (conda)
├── docker-compose.yml            # Servicio Docker
├── CLAUDE.md                     # Contexto para Claude Code
├── ADMIN_GUIDE.md                # Guia de administracion
└── *.sh                          # Scripts de operacion
```

## API Reference

### Autenticacion

```bash
# Login
curl -X POST http://localhost:8000/token \
  -d "username=usuario@mail.com&password=contraseña"
# → {"access_token": "eyJ...", "token_type": "bearer", "user": {...}}

# Registro
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user@mail.com","email":"user@mail.com","password":"pass","full_name":"Nombre"}'
```

### Consultas

```bash
# Query RAG
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"¿Que es el efecto Zeeman?","conversation_id":null}'
# → {"answer": "...", "sources": [...], "conversation_id": 5, "response_time": 42.3}
```

### Conversaciones

```bash
# Listar
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/conversations

# Ver una
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/conversations/5

# Eliminar
curl -X DELETE -H "Authorization: Bearer TOKEN" http://localhost:8000/conversations/5
```

## Configuracion

Archivo `.env`:

| Variable | Default | Descripcion |
|---|---|---|
| `OLLAMA_BASE_URL` | http://localhost:11434 | URL de Ollama |
| `EMBEDDINGS_MODEL` | nomic-embed-text | Modelo de embeddings |
| `LLM_MODEL` | deepseek-chat | Modelo del LLM |
| `DEEPSEEK_API_KEY` | - | Clave API de DeepSeek |
| `DEEPSEEK_BASE_URL` | https://api.deepseek.com | URL base de DeepSeek |
| `CHROMA_PATH` | ./data/chroma | Directorio de ChromaDB |
| `CHUNK_SIZE` | 1500 | Tamano de chunks (chars) |
| `CHUNK_OVERLAP` | 300 | Overlap entre chunks |
| `LLM_TEMPERATURE` | 0.4 | Temperatura del LLM |
| `LLM_MAX_TOKENS` | 4000 | Max tokens de respuesta |

## Problemas Comunes

| Problema | Causa | Solucion |
|---|---|---|
| Ecuaciones cortadas | max_tokens bajo | Subir LLM_MAX_TOKENS (ahora 4000) |
| LaTeX roto en chat | Marked.js corrompe `$` | Sistema de placeholders en frontend |
| Unicode math en texto | DeepSeek duplica ecuaciones | Post-procesamiento en rag_engine.py |
| Consultas lentas (~45s) | Busqueda en 7 libros + LLM | Normal. Reducir chunks_per_source |
| 401 Unauthorized | Token JWT expirado (7 dias) | Re-login |
| Examen atascado | Todas las respuestas ya enviadas | get_active_exam() retorna None |
| Backend no arranca | Puerto 8000 ocupado | `pkill -f uvicorn; sleep 3` |

## Licencia

Proyecto academico - FESC-UNAM
