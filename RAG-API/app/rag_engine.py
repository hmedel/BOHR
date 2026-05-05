from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import requests
import hashlib
import logging
from typing import List, Dict
from .config import settings
import asyncio
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self):
        """Initialize RAG Engine with embeddings and vector store."""
        try:
            self.embeddings = OllamaEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.EMBEDDINGS_MODEL
            )
            
            self.vectorstore = Chroma(
                persist_directory=settings.CHROMA_PATH,
                embedding_function=self.embeddings,
                collection_name="documents"
            )
            
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            # Get batch size from settings
            self.batch_size = getattr(settings, 'BATCH_SIZE', 50)
            
            logger.info(f"✅ RAG Engine initialized")
            logger.info(f"   Embeddings: {settings.EMBEDDINGS_MODEL}")
            logger.info(f"   Batch size: {self.batch_size}")
            logger.info(f"   Vector DB: {settings.CHROMA_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Engine: {e}")
            raise
    
    async def process_document(self, file_path: str, filename: str) -> str:
        """Process and store document with improved batch processing."""
        start_time = time.time()
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Generate unique document ID
            doc_id = hashlib.md5(filename.encode()).hexdigest()
            
            # Split text into chunks
            texts = self.text_splitter.split_text(content)
            total_chunks = len(texts)
            
            logger.info(f"📄 Processing: {filename}")
            logger.info(f"   Total chunks: {total_chunks}")
            
            # Process in configurable batches
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * self.batch_size
                end_idx = min((batch_num + 1) * self.batch_size, total_chunks)
                batch_texts = texts[start_idx:end_idx]
                
                # Create documents with metadata
                documents = [
                    Document(
                        page_content=text,
                        metadata={
                            "source": filename,
                            "doc_id": doc_id,
                            "chunk_id": start_idx + i,
                            "total_chunks": total_chunks
                        }
                    )
                    for i, text in enumerate(batch_texts)
                ]
                
                # Add documents to vector store
                self.vectorstore.add_documents(documents)
                
                # Progress logging
                progress = ((batch_num + 1) / total_batches) * 100
                logger.info(f"   Batch {batch_num + 1}/{total_batches} ({progress:.1f}%)")
                
                # Small delay to avoid overwhelming Ollama
                if batch_num < total_batches - 1:
                    await asyncio.sleep(0.1)
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ Document processed: {filename}")
            logger.info(f"   Time: {elapsed_time:.2f}s")
            logger.info(f"   Doc ID: {doc_id}")
            
            return doc_id
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {e}")
            raise
    
    def _call_llm(self, prompt: str) -> str:
        """Call DeepSeek LLM with proper error handling and retry logic."""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": settings.LLM_MAX_TOKENS,
                        "temperature": settings.LLM_TEMPERATURE
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                elif response.status_code == 429:  # Rate limit
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        raise Exception("Rate limit exceeded after retries")
                else:
                    raise Exception(f"API error (status {response.status_code}): {response.text}")
                    
            except requests.Timeout:
                if attempt < max_retries - 1:
                    logger.warning(f"Request timeout, retrying ({attempt + 1}/{max_retries})...")
                    continue
                else:
                    raise Exception("Request timeout after retries")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Error calling LLM: {e}, retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise
    
    async def query(self, query: str, top_k: int = 1, max_context: int = 500) -> Dict:
        """Query the RAG system with improved context handling."""
        try:
            # Search for relevant documents
            results = self.vectorstore.similarity_search(query, k=top_k)
            
            if not results:
                logger.info(f"No results found for query: {query}")
                return {
                    "answer": "No encontré información relevante en los documentos cargados.",
                    "sources": [],
                    "context_used": ""
                }
            
            # Aggregate context from multiple results if available
            contexts = []
            sources = set()
            total_context_length = 0
            
            for result in results:
                if total_context_length < max_context:
                    remaining = max_context - total_context_length
                    chunk = result.page_content[:remaining]
                    contexts.append(chunk)
                    total_context_length += len(chunk)
                    sources.add(result.metadata.get("source", "unknown"))
            
            # Join contexts
            context = "\n---\n".join(contexts)
            
            # Build enhanced prompt
            prompt = f"""Eres un tutor experto en química y física. Usa el siguiente contexto para responder la pregunta.

CONTEXTO RELEVANTE:
{context}

PREGUNTA DEL ESTUDIANTE:
{query}

INSTRUCCIONES:
- Responde SOLO basándote en el contexto proporcionado
- Sé claro, preciso y educativo
- Si la información no está completa en el contexto, indícalo
- Usa ejemplos cuando sea apropiado
- Estructura tu respuesta de forma lógica

RESPUESTA:"""
            
            # Call LLM
            answer = self._call_llm(prompt)
            
            # Log successful query
            logger.info(f"Query processed successfully: {query[:50]}...")
            
            return {
                "answer": answer,
                "sources": list(sources),
                "context_used": context[:200] + "..." if len(context) > 200 else context
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": f"Lo siento, ocurrió un error al procesar tu pregunta. Por favor, intenta de nuevo.",
                "sources": [],
                "context_used": ""
            }
    
    async def list_documents(self) -> List[Dict]:
        """List all documents in the system with additional metadata."""
        try:
            collection = self.vectorstore._collection
            results = collection.get()
            
            # Group by document
            docs = {}
            for metadata in results['metadatas']:
                if 'source' in metadata:
                    source = metadata['source']
                    if source not in docs:
                        docs[source] = {
                            "filename": source,
                            "doc_id": metadata.get('doc_id', hashlib.md5(source.encode()).hexdigest()),
                            "chunks": 0
                        }
                    docs[source]["chunks"] += 1
            
            return list(docs.values())
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    async def delete_document(self, doc_id: str):
        """Delete a document from the vector store."""
        try:
            self.vectorstore._collection.delete(where={"doc_id": doc_id})
            logger.info(f"Document {doc_id} deleted successfully")
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            raise
