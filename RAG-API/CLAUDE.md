# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG-API is a custom Retrieval-Augmented Generation (RAG) system designed for educational purposes in chemistry/physics. It combines **Ollama embeddings** (local) with **DeepSeek LLM** (API) to provide document-based question answering with JWT authentication and conversation history.

## Architecture

### Core Components

**Vector Database Flow:**
- Uses ChromaDB for local vector storage (`data/chroma/`)
- Embeddings generated via Ollama (`nomic-embed-text:latest`)
- Documents chunked with overlap (default: 500 chars, 50 overlap)
- Each document gets MD5-based `doc_id` for tracking

**LLM Provider:**
- DeepSeek API for chat completions (`deepseek-chat` model)
- Direct HTTP calls in `rag_engine.py:_call_llm()`
- No LangChain chains - simplified request/response pattern

**Authentication & Persistence:**
- JWT tokens (7-day expiration) via `python-jose`
- SQLite database (`data/rag_system.db`) for users, conversations, messages
- All RAG endpoints require authentication via `Depends(get_current_user)`

### Request Flow

1. **Upload**: `POST /upload` → Save file → Batch process chunks (size 20) → Store in ChromaDB with metadata
2. **Query**: `POST /query` → Retrieve conversation → Vector search (top_k) → Generate prompt → Call DeepSeek → Save to DB → Return with conversation_id
3. **Conversation**: Each query creates/updates SQLite conversation with full message history

### Key Design Decisions

- **Batched document processing**: Files split into batches of 20 chunks to avoid Ollama rate limits (see `rag_engine.py:38-58`)
- **Synchronous LLM calls**: Uses `requests.post()` instead of async clients for simplicity
- **Metadata tracking**: Each chunk stores `source`, `doc_id`, `chunk_id` for provenance
- **Context limiting**: Query responses limited by `max_context` parameter to control token usage

## Development Commands

### Setup

```bash
# Initial setup (creates venv, installs deps)
./setup_project.sh

# Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the System

```bash
# Activate environment
source venv/bin/activate

# Start backend (port 8000)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run in background with logs
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &

# Start frontend (port 9000)
cd frontend && python -m http.server 9000

# Docker deployment
docker-compose up --build
```

### Document Management

```bash
# Load documents from /home/medel/BOHR/Books (interactive)
./load_books.sh

# Load remaining documents
./load_remaining.sh

# Manual upload via API
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.md"
```

### Testing

```bash
# Full system test (checks backend, frontend, processes)
./full_test.sh

# Health check
curl http://localhost:8000/health

# Test query (requires auth token)
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es un átomo?", "top_k": 1, "max_context": 500}'

# List documents
curl -H "Authorization: Bearer <token>" http://localhost:8000/documents
```

## Configuration

### Environment Variables (.env)

```bash
# Required - DeepSeek API
DEEPSEEK_API_KEY=sk-...              # Get from platform.deepseek.com
DEEPSEEK_BASE_URL=https://api.deepseek.com  # Default endpoint
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.7

# Required - Ollama (must be running locally)
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDINGS_MODEL=nomic-embed-text:latest

# RAG tuning
CHUNK_SIZE=500                       # Characters per chunk
CHUNK_OVERLAP=50                     # Overlap between chunks
CHROMA_PATH=./data/chroma            # Vector DB location

# Optional
API_HOST=0.0.0.0
API_PORT=8000
```

**Important**: `SECRET_KEY` is hardcoded in `auth.py:10` - change in production!

### Prerequisites

- **Ollama running locally** with `nomic-embed-text:latest` model pulled
- Valid DeepSeek API key
- Python 3.11+ (uses `pydantic-settings`)

## Database Schema

**SQLite (`data/rag_system.db`):**

```
users
├─ id (PK)
├─ username (unique)
├─ email (unique)
└─ hashed_password (bcrypt)

conversations
├─ id (PK)
├─ user_id (FK → users)
├─ title (first 50 chars of query)
└─ created_at / updated_at

messages
├─ id (PK)
├─ conversation_id (FK → conversations)
├─ role ("user" | "assistant")
├─ content (text)
├─ sources (JSON string)
└─ context_used (text snippet)
```

**ChromaDB collection:** `documents` (stores embeddings + metadata)

## API Endpoints

### Authentication
- `POST /register` - Create user (username, email, password)
- `POST /token` - Login (returns JWT bearer token)
- `GET /users/me` - Get current user info

### RAG Operations
- `GET /health` - Health check (no auth)
- `POST /upload` - Upload document (requires auth)
- `POST /query` - Query with RAG (requires auth, returns answer + sources + conversation_id)
- `GET /conversations` - List user's conversations
- `GET /conversations/{id}` - Get conversation messages
- `GET /documents` - List indexed documents
- `DELETE /documents/{doc_id}` - Remove document from vector store

## Code Patterns

### RAG Engine Initialization

The RAG engine initializes on app startup (singleton pattern):
```python
# app/main.py:29
rag_engine = RAGEngine()  # Creates ChromaDB connection, Ollama embeddings
```

### Document Processing

Documents are processed in small batches to avoid Ollama rate limits:
```python
# app/rag_engine.py:40-58
BATCH_SIZE = 20  # Critical: prevents "too many requests" errors
for batch_num in range(total_batches):
    batch_texts = texts[start_idx:end_idx]
    documents = [Document(...) for text in batch_texts]
    self.vectorstore.add_documents(documents)
```

### LLM Calls

Direct HTTP calls to DeepSeek (not using LangChain's LLM abstraction):
```python
# app/rag_engine.py:63-74
response = requests.post(
    f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
    headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
    json={"model": settings.LLM_MODEL, "messages": [...]}
)
```

### Query with Context Limiting

Retrieval limits context to prevent token overflow:
```python
# app/rag_engine.py:76-92
results = self.vectorstore.similarity_search(query, k=top_k)
context = results[0].page_content[:max_context]  # Hard cutoff
prompt = f"Contexto: {context}\n\nPregunta: {query}\n\nResponde como tutor de química."
```

### Authentication Dependency

All protected endpoints use FastAPI dependency injection:
```python
@app.post("/query")
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),  # JWT validation
    db: Session = Depends(get_db)
):
```

## Common Issues

**Ollama connection errors:**
- Ensure Ollama is running: `ollama serve`
- Pull embeddings model: `ollama pull nomic-embed-text:latest`
- Check `OLLAMA_BASE_URL` matches actual Ollama port

**DeepSeek API errors:**
- Verify API key is valid and has credits
- Check rate limits (batched uploads help avoid this)
- Timeout set to 120s in `rag_engine.py:68`

**Document upload fails:**
- Ensure `data/uploads/` directory exists
- Only `.md` files supported in current implementation
- Large files may timeout - check batch size in processing

**Authentication issues:**
- JWT secret is hardcoded - must match across restarts
- Tokens expire after 7 days
- OAuth2PasswordBearer expects `token` endpoint (not `login`)

## Frontend

Single-page application (`frontend/index.html`):
- Vanilla JavaScript (no framework)
- Gradient purple/blue UNAM-inspired design
- Handles token storage in localStorage
- WebSocket-like chat interface
- Serves via `python -m http.server 9000`

## Port Summary

- **8000**: Backend API (FastAPI/Uvicorn)
- **9000**: Frontend (Python HTTP server)
- **11434**: Ollama server (must be running separately)
