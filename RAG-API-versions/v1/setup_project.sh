#!/bin/bash
set -e

echo "🏗️ CREANDO PROYECTO RAG CUSTOM"
echo ""

# Estructura de directorios
mkdir -p {app,data/chroma,data/uploads,logs,frontend}

# requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
langchain==0.1.5
langchain-community==0.0.19
langchain-ollama==0.0.1
chromadb==0.4.22
pypdf==4.0.1
python-multipart==0.0.6
requests==2.31.0
pydantic==2.5.3
pydantic-settings==2.1.0
aiofiles==23.2.1
python-dotenv==1.0.0
EOF

# .env
cat > .env << 'EOF'
# DeepSeek API
DEEPSEEK_API_KEY=REPLACE_WITH_YOUR_KEY

# Ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
EMBEDDINGS_MODEL=nomic-embed-text:latest

# RAG Settings
CHUNK_SIZE=150
CHUNK_OVERLAP=15
TOP_K=1
MAX_CONTEXT_LENGTH=500

# API
API_HOST=0.0.0.0
API_PORT=8000
EOF

echo ""
echo "🔑 Ingresa tu DeepSeek API Key:"
read -p "API Key: " DEEPSEEK_KEY
sed -i "s/REPLACE_WITH_YOUR_KEY/$DEEPSEEK_KEY/" .env

# Main app
cat > app/main.py << 'PYEOF'
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

from .rag_engine import RAGEngine
from .config import settings

app = FastAPI(title="Custom RAG API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Engine
rag_engine = RAGEngine()

class QueryRequest(BaseModel):
    query: str
    top_k: int = 1
    max_context: int = 500

class QueryResponse(BaseModel):
    answer: str
    sources: list
    context_used: str

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Custom RAG API"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload y procesa un documento para RAG"""
    try:
        # Guardar archivo
        file_path = f"data/uploads/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Procesar documento
        doc_id = await rag_engine.process_document(file_path, file.filename)
        
        return {
            "status": "success",
            "filename": file.filename,
            "doc_id": doc_id,
            "message": "Documento procesado correctamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query al RAG system"""
    try:
        result = await rag_engine.query(
            query=request.query,
            top_k=request.top_k,
            max_context=request.max_context
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents():
    """Lista documentos en el sistema"""
    docs = await rag_engine.list_documents()
    return {"documents": docs}

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Elimina un documento"""
    await rag_engine.delete_document(doc_id)
    return {"status": "success", "message": f"Documento {doc_id} eliminado"}

if __name__ == "__main__":
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
PYEOF

# Config
cat > app/config.py << 'PYEOF'
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # DeepSeek
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    EMBEDDINGS_MODEL: str = "nomic-embed-text:latest"
    
    # RAG
    CHUNK_SIZE: int = 150
    CHUNK_OVERLAP: int = 15
    TOP_K: int = 1
    MAX_CONTEXT_LENGTH: int = 500
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Paths
    CHROMA_PATH: str = "./data/chroma"
    UPLOADS_PATH: str = "./data/uploads"
    
    class Config:
        env_file = ".env"

settings = Settings()
PYEOF

# RAG Engine
cat > app/rag_engine.py << 'PYEOF'
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import requests
import os
import hashlib
from typing import List, Dict
from .config import settings

class RAGEngine:
    def __init__(self):
        # Embeddings
        self.embeddings = OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.EMBEDDINGS_MODEL
        )
        
        # Vector Store
        self.vectorstore = Chroma(
            persist_directory=settings.CHROMA_PATH,
            embedding_function=self.embeddings,
            collection_name="documents"
        )
        
        # Text Splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        print(f"✅ RAG Engine inicializado")
        print(f"   Embeddings: {settings.EMBEDDINGS_MODEL}")
        print(f"   Chunk size: {settings.CHUNK_SIZE}")
        print(f"   Vector DB: {settings.CHROMA_PATH}")
    
    async def process_document(self, file_path: str, filename: str) -> str:
        """Procesa y almacena un documento"""
        # Leer contenido
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generar ID único
        doc_id = hashlib.md5(filename.encode()).hexdigest()
        
        # Split en chunks
        texts = self.text_splitter.split_text(content)
        
        # Crear documentos con metadata
        documents = [
            Document(
                page_content=text,
                metadata={
                    "source": filename,
                    "doc_id": doc_id,
                    "chunk_id": i
                }
            )
            for i, text in enumerate(texts)
        ]
        
        # Agregar a vectorstore
        self.vectorstore.add_documents(documents)
        
        print(f"✅ Documento procesado: {filename}")
        print(f"   Chunks: {len(documents)}")
        print(f"   Doc ID: {doc_id}")
        
        return doc_id
    
    async def query(self, query: str, top_k: int = 1, max_context: int = 500) -> Dict:
        """Query al sistema RAG"""
        # 1. Buscar chunks relevantes
        results = self.vectorstore.similarity_search(query, k=top_k)
        
        if not results:
            return {
                "answer": "No encontré información relevante en los documentos.",
                "sources": [],
                "context_used": ""
            }
        
        # 2. Preparar contexto (LIMITADO)
        context = results[0].page_content[:max_context]
        source = results[0].metadata.get("source", "unknown")
        
        # 3. Preparar prompt
        prompt = f"""Contexto del documento:
{context}

Pregunta: {query}

Instrucciones:
- Responde basándote SOLO en el contexto proporcionado
- Sé conciso y preciso
- Si la información no está en el contexto, di "no encuentro esa información en el documento"
- Usa lenguaje claro y didáctico

Respuesta:"""
        
        # 4. Llamar a DeepSeek
        response = requests.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"DeepSeek API error: {response.text}")
        
        answer = response.json()["choices"][0]["message"]["content"]
        
        return {
            "answer": answer,
            "sources": [source],
            "context_used": context[:100] + "..."  # Preview
        }
    
    async def list_documents(self) -> List[Dict]:
        """Lista documentos en el sistema"""
        # Get unique sources from vectorstore
        collection = self.vectorstore._collection
        results = collection.get()
        
        sources = set()
        for metadata in results['metadatas']:
            if 'source' in metadata:
                sources.add(metadata['source'])
        
        return [{"filename": s, "doc_id": hashlib.md5(s.encode()).hexdigest()} for s in sources]
    
    async def delete_document(self, doc_id: str):
        """Elimina un documento"""
        collection = self.vectorstore._collection
        collection.delete(where={"doc_id": doc_id})
        print(f"✅ Documento {doc_id} eliminado")

PYEOF

# __init__.py
touch app/__init__.py

echo ""
echo "✅ Proyecto creado"
echo ""
echo "📦 Instalando dependencias..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ Setup completo"
