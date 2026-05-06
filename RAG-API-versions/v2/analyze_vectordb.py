#!/usr/bin/env python3
"""Análisis completo de la base de datos vectorial ChromaDB"""

import chromadb
from pathlib import Path
from collections import Counter
import sys

# Agregar app al path para importar config
sys.path.insert(0, './app')
from config import settings

def main():
    # Conectar a ChromaDB
    client = chromadb.PersistentClient(path="./data/chroma")
    collection = client.get_collection("documents")
    
    # Estadísticas generales
    count = collection.count()
    print(f"\n📊 ESTADÍSTICAS CHROMADB")
    print(f"{'='*60}")
    print(f"Total de chunks indexados: {count}")
    
    # Obtener todos los documentos
    results = collection.get()
    
    # Analizar distribución por fuente
    sources = [m['source'] for m in results['metadatas'] if 'source' in m]
    source_stats = Counter(sources)
    
    print(f"\n📚 DISTRIBUCIÓN POR FUENTE:")
    print(f"{'='*60}")
    for source, chunk_count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
        if not source.startswith('test_'):
            print(f"  {source[:50]:<50} {chunk_count:>6} chunks")
    
    # Analizar tamaño de chunks
    print(f"\n📏 ANÁLISIS DE TAMAÑO DE CHUNKS:")
    print(f"{'='*60}")
    documents = results['documents']
    chunk_lengths = [len(doc) for doc in documents]
    if chunk_lengths:
        avg_len = sum(chunk_lengths) / len(chunk_lengths)
        min_len = min(chunk_lengths)
        max_len = max(chunk_lengths)
        print(f"  Promedio: {avg_len:.0f} caracteres")
        print(f"  Mínimo:   {min_len} caracteres")
        print(f"  Máximo:   {max_len} caracteres")
    
    # Buscar chunks que contengan "Hamiltonian" o "hamiltoniano"
    print(f"\n🔍 BÚSQUEDA DE 'HAMILTONIAN' EN CHUNKS:")
    print(f"{'='*60}")
    hamiltonian_chunks = []
    for i, doc in enumerate(documents):
        if 'hamiltonian' in doc.lower() or 'hamiltoniano' in doc.lower():
            source = results['metadatas'][i].get('source', 'unknown')
            if not source.startswith('test_'):
                hamiltonian_chunks.append({
                    'source': source,
                    'length': len(doc),
                    'preview': doc[:300] + "..." if len(doc) > 300 else doc
                })
    
    print(f"  Chunks encontrados con 'Hamiltonian': {len(hamiltonian_chunks)}")
    
    # Mostrar primeros 5 chunks de ejemplo
    for i, chunk in enumerate(hamiltonian_chunks[:5]):
        print(f"\n  Ejemplo {i+1}:")
        print(f"    Fuente: {chunk['source']}")
        print(f"    Tamaño: {chunk['length']} chars")
        print(f"    Preview: {chunk['preview']}")
    
    # Verificar configuración actual de chunking
    print(f"\n⚙️  CONFIGURACIÓN ACTUAL (config.py):")
    print(f"{'='*60}")
    print(f"  CHUNK_SIZE:    {settings.CHUNK_SIZE}")
    print(f"  CHUNK_OVERLAP: {settings.CHUNK_OVERLAP}")
    print(f"  EMBEDDINGS:    {settings.EMBEDDINGS_MODEL}")
    
    # Buscar ecuaciones matemáticas (LaTeX patterns)
    print(f"\n🔬 BÚSQUEDA DE ECUACIONES MATEMÁTICAS:")
    print(f"{'='*60}")
    equation_patterns = ['$$', '\\hat', '\\frac', '\\nabla', 'H_2', r'\hbar']
    equation_chunks = []
    
    for pattern in equation_patterns:
        count = sum(1 for doc in documents if pattern in doc)
        print(f"  Chunks con '{pattern}': {count}")
        
        # Recopilar ejemplos
        for i, doc in enumerate(documents):
            if pattern in doc and len(equation_chunks) < 3:
                source = results['metadatas'][i].get('source', 'unknown')
                if not source.startswith('test_') and 'hamiltonian' in doc.lower():
                    equation_chunks.append({
                        'source': source,
                        'pattern': pattern,
                        'preview': doc[:400] + "..." if len(doc) > 400 else doc
                    })
    
    # Mostrar chunks con ecuaciones y "hamiltonian"
    if equation_chunks:
        print(f"\n📐 CHUNKS CON ECUACIONES Y 'HAMILTONIAN':")
        print(f"{'='*60}")
        for i, chunk in enumerate(equation_chunks[:3]):
            print(f"\n  Ejemplo {i+1} (patrón: {chunk['pattern']}):")
            print(f"    Fuente: {chunk['source']}")
            print(f"    Contenido:\n{chunk['preview']}\n")
    
    # DIAGNÓSTICO FINAL
    print(f"\n🩺 DIAGNÓSTICO:")
    print(f"{'='*60}")
    
    if avg_len < 300:
        print("  ⚠️  PROBLEMA: Chunks muy pequeños (promedio < 300 chars)")
        print("     → Recomendación: Aumentar CHUNK_SIZE a 800-1000")
    
    if len(hamiltonian_chunks) < 50:
        print(f"  ⚠️  PROBLEMA: Pocos chunks con 'Hamiltonian' ({len(hamiltonian_chunks)} encontrados)")
        print("     → Causa probable: Información fragmentada o ausente")
        print("     → Recomendación: Agregar libros especializados en química cuántica")
    
    if settings.CHUNK_OVERLAP < 100:
        print(f"  ⚠️  PROBLEMA: Overlap muy bajo ({settings.CHUNK_OVERLAP} chars)")
        print("     → Recomendación: Aumentar CHUNK_OVERLAP a 150-200")
    
    print(f"\n✅ Análisis completado\n")

if __name__ == "__main__":
    main()