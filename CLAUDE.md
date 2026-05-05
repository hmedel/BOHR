# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BOHR contains multiple RAG (Retrieval-Augmented Generation) systems for educational purposes, specifically focused on "Estructura de la Materia" (Material Structure). The repository uses a **multi-version architecture** with parallel development of different system iterations.

## Repository Structure

```
BOHR/
├── rag_api/              # LibreChat-compatible RAG API (ID-based document indexing)
├── RAG-API/              # Alternative RAG implementation
├── RAG-API-versions/     # Versioned RAG systems
│   ├── v1/               # Stable basic system (ALWAYS FUNCTIONAL - FALLBACK)
│   │   ├── app/          # Backend application
│   │   └── frontend/     # Simple frontend (port 9001)
│   └── v2/               # Advanced system with authentication & analytics
│       ├── app/          # Main application code
│       │   ├── main.py            # FastAPI app with exam system
│       │   ├── rag_engine.py      # RAG core logic
│       │   ├── exam_engine.py     # Exam generation & evaluation
│       │   ├── analytics_engine.py # User query analytics
│       │   ├── qualitative_evaluator.py # Bloom/SOLO evaluation
│       │   ├── database.py        # SQLAlchemy models
│       │   ├── auth.py            # JWT authentication
│       │   └── config.py          # Configuration
│       ├── frontend/     # Enhanced frontend with UNAM branding (port 9000)
│       ├── data/         # Vector database & SQLite data
│       └── backups/      # System backups
├── Books/                # Educational PDF materials
├── scripts/              # Utility scripts
└── Backups/              # Historical backups
```

## Key Architecture Concepts

### Multi-Version System

The RAG-API-versions directory implements a **blue-green deployment pattern** with version fallback:

- **v1**: Basic RAG system without authentication, persistent history, or analytics (ports 8001/9001)
  - Always kept functional as fallback
  - Uses simple HTTP server for frontend
  - No user management

- **v2**: Full-featured system (ports 8000/9000)
  - Multi-user authentication (JWT-based)
  - SQLite database for persistent history
  - Chromadb for vector storage
  - Real-time analytics and progress tracking
  - Bloom taxonomy and SOLO level evaluation
  - Interactive exam system with immediate feedback
  - Enhanced frontend with markdown & LaTeX support

### RAG API (rag_api/)

This is a **LibreChat-compatible** RAG API that provides:
- **ID-based document indexing**: Documents organized by `file_id`
- **Multiple vector store backends**: PostgreSQL/pgvector (default) or MongoDB Atlas
- **Multiple embedding providers**: OpenAI, Azure, HuggingFace, Ollama, Bedrock, Vertex AI, Google GenAI
- **Async operations**: Built on FastAPI with async/await throughout
- **JWT authentication**: Optional security middleware

### V2 Educational Features

**Exam System** (exam_engine.py):
- Detects exam requests via pattern matching
- Generates questions dynamically based on student history
- Supports multiple question types (multiple choice, open-ended)
- Progressive difficulty using Bloom's taxonomy levels
- Immediate feedback after each answer
- Uses SOLO taxonomy for answer evaluation
- Final summary with strengths and improvement plans

**Analytics** (analytics_engine.py):
- Sentiment analysis of student queries
- Topic detection and tracking
- Query complexity assessment
- Learning pattern identification

**Qualitative Evaluation** (qualitative_evaluator.py):
- Bloom's taxonomy classification (Remember → Create)
- SOLO taxonomy assessment (Prestructural → Extended Abstract)
- Constructive feedback generation

## Development Commands

### rag_api (LibreChat-compatible API)

```bash
# Setup
cd rag_api
pip install -r requirements.txt
pip install -r test_requirements.txt  # For testing

# Run locally
uvicorn main:app --host 0.0.0.0 --port 8000

# Run with hot reload
uvicorn main:app --reload

# Docker
docker compose up              # Full stack (DB + API)
docker compose -f db-compose.yaml up    # Database only
docker compose -f api-compose.yaml up   # API only

# Tests
pytest                         # Run all tests
pytest tests/test_main.py      # Specific test file
pytest -v                      # Verbose output
pytest -k "test_name"          # Run specific test
```

### RAG-API-versions (Educational System)

```bash
# Version management scripts (run from RAG-API-versions/)
./switch_version.sh            # Interactive version switcher
./status.sh                    # Check running services
./rollback.sh                  # Emergency rollback to v1

# Start v1 (stable)
cd v1
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > server.log 2>&1 &
cd frontend && nohup python -m http.server 9001 > frontend.log 2>&1 &

# Start v2 (development)
cd v2
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
cd frontend && nohup python -m http.server 9000 > frontend.log 2>&1 &

# View logs
tail -f v1/server.log          # v1 backend logs
tail -f v2/server.log          # v2 backend logs
tail -f v2/server_final.log    # Production logs

# Testing v2
cd v2
./full_test.sh                 # Complete system test
./load_books.sh                # Load PDF documents
```

## Configuration

### rag_api Environment Variables

**Required:**
- `RAG_OPENAI_API_KEY`: OpenAI API key for embeddings (or use `EMBEDDINGS_PROVIDER`)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database credentials
- `DB_HOST`, `DB_PORT`: PostgreSQL connection info

**Vector Database:**
- `VECTOR_DB_TYPE`: "pgvector" (default) or "atlas-mongo"
- `COLLECTION_NAME`: Vector collection name
- For MongoDB: `ATLAS_MONGO_DB_URI`, `ATLAS_SEARCH_INDEX`

**Embeddings:**
- `EMBEDDINGS_PROVIDER`: "openai", "azure", "huggingface", "huggingfacetei", "ollama", "bedrock", "google_genai", "vertexai"
- `EMBEDDINGS_MODEL`: Model name for the provider
- Provider-specific keys: `RAG_AZURE_OPENAI_API_KEY`, `HF_TOKEN`, `AWS_ACCESS_KEY_ID`, etc.

**Optional:**
- `JWT_SECRET`: Enable JWT authentication
- `DEBUG_RAG_API`: "True" for verbose logging and debug routes
- `RAG_HOST`, `RAG_PORT`: Server binding (default: 0.0.0.0:8000)
- `CHUNK_SIZE`, `CHUNK_OVERLAP`: Text splitting parameters
- `PDF_EXTRACT_IMAGES`: "True" to extract images from PDFs

### v2 Environment Variables

Create `.env` in `RAG-API-versions/v2/`:
```bash
OPENAI_API_KEY=sk-...
CHROMA_PATH=./data/chroma_db
SQLITE_PATH=./data/rag_system.db
JWT_SECRET_KEY=your-secret-key
```

## Database Architecture

### rag_api (PostgreSQL/pgvector)

The API uses async connection pooling and automatically creates:
- Vector extension and indexes on startup
- Collection tables for document embeddings
- File ID-based partitioning for efficient queries

Database operations in `app/services/database.py` and vector store factory in `app/services/vector_store/`.

### v2 (SQLite + Chromadb)

**SQLite schema** (database.py):
- `users`: Authentication and profiles
- `conversations`: Chat sessions
- `messages`: Individual messages with analytics (sentiment, Bloom level, SOLO level)
- `query_logs`: Performance tracking
- `student_progress`: Aggregated learning metrics
- `exams`: Exam instances
- `exam_responses`: Individual question responses
- `exam_results`: Final exam evaluations

**Chromadb**: Vector embeddings for document retrieval

## Code Patterns

### rag_api Patterns

**Async document loading:**
```python
# Document loading happens in thread pool to avoid blocking
app.state.thread_pool = ThreadPoolExecutor(max_workers=8)
# Used in document_routes.py for file processing
```

**Vector store factory pattern:**
```python
# app/services/vector_store/factory.py
vector_store = get_vector_store(
    connection_string=CONNECTION_STRING,
    embeddings=embeddings,
    collection_name=COLLECTION_NAME,
    mode="async"  # or "atlas-mongo"
)
```

**Middleware chain:**
- CORS middleware (allow all origins)
- LogMiddleware (structured logging)
- security_middleware (JWT verification if configured)

### v2 Patterns

**Query flow in main.py:**
1. Detect exam request → Generate exam
2. Check active exam → Handle exam response
3. Normal RAG query → Analytics → Response generation → Qualitative evaluation

**LLM calls** (rag_engine.py):
```python
def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
    # Uses OpenAI API with configurable temperature
    # Returns raw string response
```

**Exam state machine:**
- Exam request detected → Offer exam with requirements check
- Confirmation → Create exam, generate first question
- Answer received → Evaluate → Generate next question OR final summary
- Cancellation → Mark exam as cancelled

## Testing

**rag_api tests:**
- Use `conftest.py` to mock vector store and database connections
- Tests run without actual DB using `DummyVectorStore`
- Set `TESTING=1` environment variable to enable test mode

**Common test invocations:**
```bash
pytest                              # All tests
pytest tests/test_main.py          # Main API tests
pytest tests/services/             # Service layer tests
pytest -v --tb=short               # Verbose with short tracebacks
```

## Development Workflow

### Adding Features to v1
1. Test in v1 first (simpler environment)
2. Ensure backward compatibility
3. Keep v1 always functional (fallback principle)

### Developing in v2
1. Make changes in v2 directory
2. Create backup before major changes: `cp -r app backups/feature_name_$(date +%Y%m%d_%H%M%S)`
3. Test extensively with `./full_test.sh`
4. Monitor logs: `tail -f server.log`
5. If broken, rollback: `./rollback.sh`
6. Once stable, consider promoting to v1

### Working with Documents
- Place PDFs in `Books/` or `RAG-API-versions/v2/data/books/`
- Use `load_books.sh` to index documents
- Check ChromaDB collection: files stored with metadata

## Common Issues

**Vector database connection:**
- Ensure PostgreSQL has pgvector extension: `CREATE EXTENSION vector;`
- For RDS: Must use PostgreSQL 12.16-R2, 13.12-R2, 14.9-R2, or 15.4-R2+

**v2 exam system:**
- Exam questions stored in exam_data JSON field
- Active exam detected by checking for incomplete responses
- Pattern matching for exam requests can be extended in `is_exam_request()`

**Authentication:**
- v1: No authentication
- v2: JWT tokens with configurable expiration
- rag_api: Optional JWT via `JWT_SECRET` env var

## Port Summary
- 8000: v2 backend (development)
- 8001: v1 backend (stable)
- 9000: v2 frontend
- 9001: v1 frontend
- 5432: PostgreSQL (rag_api)
- 27017/27018: MongoDB (optional)
