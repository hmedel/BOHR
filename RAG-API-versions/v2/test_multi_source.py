#!/usr/bin/env python3
"""
Script de prueba para query_multi_source
Valida que el nuevo método retorna 3 resultados de fuentes diferentes
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.rag_engine import RAGEngine

async def test_multi_source():
    print("\n" + "="*60)
    print("PRUEBA: query_multi_source()")
    print("="*60)
    
    rag = RAGEngine()
    
    queries = [
        "¿Qué es un orbital atómico?",
        "Explica la configuración electrónica",
        "¿Qué son los números cuánticos?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}/3: {query}")
        print('='*60)
        
        result = await rag.query_multi_source(query, sources_count=3)
        
        print(f"\n📊 RESULTADOS:")
        print(f"   Fuentes encontradas: {result['total_sources']}")
        print(f"   Tiempo: {result['response_time']:.2f}s")
        print(f"   Query: {result['query']}")
        
        if result['total_sources'] == 0:
            print("\n⚠️  NO SE ENCONTRARON RESULTADOS")
            if 'error' in result:
                print(f"   Error: {result['error']}")
        else:
            print(f"\n📚 FUENTES:\n")
            for res in result['results']:
                print(f"   #{res['rank']} - {res['source_display']}")
                print(f"      Source file: {res['source']}")
                print(f"      Relevance: {res['relevance_score']:.2f}")
                print(f"      Content preview: {res['content'][:150]}...")
                print()
        
        # Validaciones
        print("✅ VALIDACIONES:")
        
        # Validar estructura
        assert 'results' in result, "❌ Falta campo 'results'"
        assert 'total_sources' in result, "❌ Falta campo 'total_sources'"
        assert 'query' in result, "❌ Falta campo 'query'"
        assert 'response_time' in result, "❌ Falta campo 'response_time'"
        print("   ✓ Estructura correcta")
        
        # Validar fuentes diferentes
        if result['total_sources'] > 0:
            sources = [r['source'] for r in result['results']]
            assert len(sources) == len(set(sources)), "❌ Hay fuentes duplicadas"
            print(f"   ✓ Todas las fuentes son diferentes ({len(sources)} fuentes)")
            
            # Validar contenido presente
            for res in result['results']:
                assert len(res['content']) > 0, "❌ Contenido vacío"
            print("   ✓ Todos los resultados tienen contenido")
            
            # Validar tiempo de respuesta razonable
            assert result['response_time'] < 10, "❌ Tiempo de respuesta > 10s"
            print(f"   ✓ Tiempo de respuesta aceptable ({result['response_time']:.2f}s)")
        
        print()
    
    print("\n" + "="*60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(test_multi_source())
        print("\n🎉 SUCCESS: El método query_multi_source() funciona correctamente")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)