# BOHR — Asistente RAG para Estructura de la Materia

Sistema educativo de Recuperación-Generación Aumentada (RAG) para el curso **Estructura de la Materia** en la Facultad de Estudios Superiores Cuautitlán (FESC-UNAM). Permite a los estudiantes consultar material bibliográfico, recibir respuestas con soporte LaTeX, y realizar exámenes formativos adaptativos.

**URLs públicas:**
- Chat: [https://chat.bohrbot.space](https://chat.bohrbot.space)
- API: [https://api.bohrbot.space](https://api.bohrbot.space)

---

## Características principales

- **Búsqueda semántica** sobre 7 libros de física y química (11,800+ fragmentos indexados)
- **Respuestas con LaTeX** — ecuaciones renderizadas con KaTeX directamente en el chat
- **Streaming** — las respuestas aparecen token por token sin esperar al final
- **Autenticación multiusuario** — cada estudiante tiene su propio historial (JWT, 7 días)
- **Exámenes formativos adaptativos** — 5 preguntas con dificultad ajustada al historial de cada alumno (Taxonomía de Bloom)
- **Panel de progreso** — visualización de distribución Bloom, complejidad de preguntas y temas explorados
- **Analytics para el profesor** — dashboard de participación por alumno, tiempos de respuesta y exportación CSV
- **Historial persistente** — conversaciones guardadas y accesibles entre sesiones

---

## Arquitectura

```
Frontend (puerto 9000)              Backend FastAPI (puerto 8000)
HTML + Vanilla JS                   ├── RAG Engine
KaTeX · Marked.js · highlight.js    │   ├── Ollama (nomic-embed-text) → embeddings
Cloudflare Tunnel → HTTPS           │   └── ChromaDB → búsqueda vectorial
                                    ├── LLM: DeepSeek (deepseek-chat)
                                    ├── Exam Engine (Bloom adaptativo)
                                    ├── Analytics Engine (TextBlob)
                                    ├── Qualitative Evaluator (Bloom/SOLO)
                                    ├── Auth (JWT + SHA-256)
                                    └── SQLite (8 tablas)
```

---

## Requisitos

- Python 3.10+ en entorno conda/venv
- [Ollama](https://ollama.ai) con el modelo `nomic-embed-text` instalado
- Cuenta y API key de [DeepSeek](https://platform.deepseek.com)
- (Opcional) [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) para exposición HTTPS

---

## Instalación

```bash
git clone https://github.com/hmedel/BOHR.git
cd BOHR/RAG-API-versions/v2

pip install -r requirements.txt

# Descargar modelo de embeddings
ollama pull nomic-embed-text
```

Crear el archivo `.env` (nunca se sube al repositorio):

```bash
DEEPSEEK_API_KEY=sk-tu-key-aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDINGS_MODEL=nomic-embed-text
CHROMA_PATH=./data/chroma
LLM_TEMPERATURE=0.4
LLM_MAX_TOKENS=4000
```

---

## Uso

```bash
# Backend (4 workers)
PYTHON=/path/to/your/python
$PYTHON -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 >> logs/backend_production.log 2>&1 &

# Frontend
cd frontend && python -m http.server 9000 &
```

Verificar que todo esté corriendo:

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"2.7"}
```

---

## Material bibliográfico

Los 7 libros indexados cubren física atómica, mecánica cuántica y química inorgánica:

| Libro | Fragmentos |
|---|---|
| Atomic Spectra and Atomic Structure | 496 |
| Atoms, Molecules and Photons | 1,667 |
| Bransden & Joachain — Physics of Atoms and Molecules | 1,454 |
| Huheey — Inorganic Chemistry | 2,734 |
| Introduction to the Structure of Matter | 2,041 |
| Cruz-Garritz — Estructura Atómica: Un Enfoque Químico | 1,522 |
| Old Quantum Theory & Early QM | 1,898 |

Para agregar un nuevo libro: convertir a Markdown, colocar en `data/uploads/` y ejecutar `./load_books.sh`.

---

## Administración

### Alta de usuarios (individual)

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"correo@gmail.com","email":"correo@gmail.com","password":"numeroCuenta","full_name":"Nombre Completo"}'
```

### Alta masiva desde CSV

```bash
# CSV con columnas: ESTUDIANTE,Email,Cuenta
while IFS=, read -r nombre email cuenta; do
  [ -z "$email" ] && continue
  curl -s -X POST http://localhost:8000/register \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"$email\",\"email\":\"$email\",\"password\":\"$cuenta\",\"full_name\":\"$nombre\"}"
done < <(tail -n +2 alumnos.csv)
```

### Dashboard de analytics (solo admins)

Abrir en navegador: `https://api.bohrbot.space/analytics?token=<JWT>`

O desde el chat: iniciar sesión como admin → botón **📊 Analytics**.

### Backup de la base de datos

```bash
./backup_db.sh
# Crea data/backups/rag_system_FECHA.db y conserva los últimos 4 backups
```

### Estadísticas rápidas

```bash
sqlite3 -header -column data/rag_system.db "
SELECT 'Usuarios' as tabla, COUNT(*) FROM users
UNION ALL SELECT 'Mensajes', COUNT(*) FROM messages
UNION ALL SELECT 'Exámenes completados', COUNT(*) FROM exams WHERE status='completed';"
```

---

## Endpoints principales

| Endpoint | Método | Auth | Descripción |
|---|---|---|---|
| `/health` | GET | No | Estado del sistema |
| `/register` | POST | No | Crear usuario |
| `/token` | POST | No | Login (OAuth2) |
| `/query` | POST | JWT | Consulta RAG completa |
| `/query/stream` | POST | JWT | Consulta con streaming SSE |
| `/me/progress` | GET | JWT | Progreso del estudiante |
| `/me/progress/export` | GET | JWT | Exportar historial (CSV) |
| `/me/exam/cancel` | POST | JWT | Cancelar examen activo |
| `/conversations` | GET | JWT | Listar conversaciones |
| `/analytics` | GET | Admin | Dashboard de participación |
| `/documents` | GET | JWT | Libros indexados |

---

## Versiones

El repositorio mantiene dos versiones en paralelo:

| Versión | Puerto backend | Puerto frontend | Descripción |
|---|---|---|---|
| **v2** (activa) | 8000 | 9000 | Sistema completo con auth, exámenes y analytics |
| **v1** (fallback) | 8001 | 9001 | Sistema básico sin autenticación |

Para cambiar entre versiones: `./switch_version.sh` desde `RAG-API-versions/`.

---

## Estructura del repositorio

```
BOHR/
├── RAG-API-versions/
│   ├── v2/                     # Sistema principal (producción)
│   │   ├── app/                # Backend FastAPI
│   │   │   ├── main.py         # Endpoints y flujo de estado
│   │   │   ├── rag_engine.py   # Búsqueda vectorial y síntesis
│   │   │   ├── exam_engine.py  # Exámenes adaptativos
│   │   │   ├── analytics_engine.py
│   │   │   ├── qualitative_evaluator.py
│   │   │   ├── database.py     # Modelos SQLAlchemy
│   │   │   ├── auth.py
│   │   │   └── config.py       # Lee configuración desde .env
│   │   ├── frontend/
│   │   │   ├── index.html      # SPA completa
│   │   │   └── config.js       # Detección dev/prod automática
│   │   ├── data/               # ChromaDB + SQLite (no versionados)
│   │   ├── logs/               # Logs de producción (no versionados)
│   │   ├── backup_db.sh        # Backup manual de la DB
│   │   ├── analyze_participation.py
│   │   ├── ADMIN_GUIDE.md      # Guía operativa completa
│   │   └── requirements.txt
│   └── v1/                     # Fallback estable
├── RAG-API/                    # Implementación alternativa (referencia)
├── CLAUDE.md                   # Guía para Claude Code
└── README.md                   # Este archivo
```

---

## Seguridad

- Las API keys y secrets van **únicamente en `.env`** — nunca en el código
- CORS restringido a `chat.bohrbot.space` y `localhost:9000`
- Rate limiting: `/register` 10 req/min, `/token` 20 req/min
- Contraseñas hasheadas con SHA-256
- Tokens JWT con expiración de 7 días

---

## Licencia

Proyecto educativo interno — FESC-UNAM. No redistribuir sin autorización.
