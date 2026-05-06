#!/usr/bin/env python3
"""
Script de reindexación optimizada para ChromaDB
Corrige problema de chunks muy pequeños (promedio 101 chars)
"""

import sys
import os
import asyncio
from pathlib import Path

# Configurar path para imports absolutos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports absolutos
from app.rag_engine import RAGEngine
from app.config import settings

async def reindex_all():
    print(f"\n📊 CONFIGURACIÓN DE CHUNKING:")
    print(f"{'='*60}")
    print(f"  CHUNK_SIZE:    {settings.CHUNK_SIZE}")
    print(f"  CHUNK_OVERLAP: {settings.CHUNK_OVERLAP}")
    print(f"  EMBEDDINGS:    {settings.EMBEDDINGS_MODEL}")
    print("")
    
    print(f"🔧 Inicializando RAG Engine...")
    engine = RAGEngine()
    print(f"   ✅ Engine inicializado")
    print("")
    
    # Obtener archivos .md (excluyendo test_*)
    uploads_dir = Path("./data/uploads")
    md_files = [f for f in uploads_dir.glob("*.md") if not f.name.startswith("test_")]
    
    print(f"📚 Procesando {len(md_files)} documentos...")
    print(f"{'='*60}")
    print("")
    
    for i, file_path in enumerate(sorted(md_files), 1):
        print(f"[{i}/{len(md_files)}] Indexando: {file_path.name}")
        try:
            doc_id = await engine.process_document(str(file_path), file_path.name)
            print(f"   ✅ Completado - doc_id: {doc_id[:8]}...")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:100]}")
        print("")
    
    # Verificar total de chunks creados
    collection = engine.vectorstore._collection
    total_chunks = collection.count()
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTADO FINAL:")
    print(f"{'='*60}")
    print(f"  Total de chunks indexados: {total_chunks:,}")
    print(f"  Promedio por documento:    {total_chunks / len(md_files):.0f} chunks")
    print(f"  Tamaño esperado por chunk: ~{settings.CHUNK_SIZE} caracteres")
    print("")

if __name__ == "__main__":
    asyncio.run(reindex_all())