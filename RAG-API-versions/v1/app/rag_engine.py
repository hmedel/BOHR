from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import requests
import hashlib
from typing import List, Dict
from .config import settings

class RAGEngine:
    def __init__(self):
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
        
        print("RAG Engine inicializado con BATCH_SIZE=20")
    
    async def process_document(self, file_path: str, filename: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_id = hashlib.md5(filename.encode()).hexdigest()
        texts = self.text_splitter.split_text(content)
        
        print(f"Total chunks: {len(texts)}")
        
        # BATCH SIZE MUY PEQUEÑO para evitar límites
        BATCH_SIZE = 20
        total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_num in range(total_batches):
            start_idx = batch_num * BATCH_SIZE
            end_idx = min((batch_num + 1) * BATCH_SIZE, len(texts))
            batch_texts = texts[start_idx:end_idx]
            
            documents = [
                Document(
                    page_content=text,
                    metadata={"source": filename, "doc_id": doc_id, "chunk_id": start_idx + i}
                )
                for i, text in enumerate(batch_texts)
            ]
            
            self.vectorstore.add_documents(documents)
            print(f"Batch {batch_num + 1}/{total_batches} OK")
        
        print(f"Documento completo: {len(texts)} chunks")
        return doc_id
    
    def _call_llm(self, prompt: str) -> str:
        response = requests.post(
            f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={"model": settings.LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": settings.LLM_MAX_TOKENS, "temperature": settings.LLM_TEMPERATURE},
            timeout=120
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.text}")
        
        return response.json()["choices"][0]["message"]["content"]
    
    async def query(self, query: str, top_k: int = 1, max_context: int = 500) -> Dict:
        results = self.vectorstore.similarity_search(query, k=top_k)
        
        if not results:
            return {"answer": "No encontré información relevante.", "sources": [], "context_used": ""}
        
        context = results[0].page_content[:max_context]
        source = results[0].metadata.get("source", "unknown")
        
        prompt = f"Contexto: {context}\n\nPregunta: {query}\n\nResponde como tutor de química."
        
        try:
            answer = self._call_llm(prompt)
        except Exception as e:
            answer = f"Error: {str(e)}"
        
        return {"answer": answer, "sources": [source], "context_used": context[:100] + "..."}
    
    async def list_documents(self) -> List[Dict]:
        collection = self.vectorstore._collection
        results = collection.get()
        sources = set(m['source'] for m in results['metadatas'] if 'source' in m)
        return [{"filename": s, "doc_id": hashlib.md5(s.encode()).hexdigest()} for s in sources]
    
    async def delete_document(self, doc_id: str):
        self.vectorstore._collection.delete(where={"doc_id": doc_id})
