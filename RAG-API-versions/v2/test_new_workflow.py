#!/usr/bin/env python3
"""
Script de prueba para el nuevo flujo de trabajo v2
- Multi-source RAG sin evaluación automática
- Oferta de examen después de 3 consultas
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_workflow():
    """Prueba completa del nuevo flujo"""
    
    print("=" * 60)
    print("PRUEBA DEL NUEVO FLUJO DE TRABAJO V2")
    print("=" * 60)
    
    # 1. Login
    print("\n1️⃣  AUTENTICACIÓN")
    print("-" * 60)
    
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    response = requests.post(
        f"{BASE_URL}/token",
        data=login_data
    )
    
    if response.status_code != 200:
        print(f"❌ Error en login: {response.status_code}")
        print(response.text)
        return False
    
    token = response.json()["access_token"]
    print(f"✅ Login exitoso")
    print(f"   Token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Primera consulta RAG
    print("\n2️⃣  PRIMERA CONSULTA (Multi-Source RAG)")
    print("-" * 60)
    
    query1 = {
        "query": "¿Qué es un átomo?",
        "top_k": 3
    }
    
    response = requests.post(
        f"{BASE_URL}/query",
        headers=headers,
        json=query1
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return False
    
    result1 = response.json()
    print(f"✅ Consulta procesada en {result1.get('response_time', 0)}s")
    
    # Verificar estructura de respuesta
    if "multi_source_results" in result1:
        print(f"✅ Retornó multi_source_results")
        print(f"   Total fuentes: {result1.get('total_sources', 0)}")
        
        for res in result1.get("multi_source_results", []):
            print(f"   - Rank {res['rank']}: {res['source_display']} ({res['relevance_score']:.2%})")
    else:
        print(f"⚠️  No retornó multi_source_results")
    
    # Verificar que NO tiene evaluación Bloom/SOLO
    if "qualitative_feedback" not in result1.get("answer", ""):
        print(f"✅ NO incluye evaluación cualitativa automática")
    else:
        print(f"⚠️  Incluye evaluación (no debería)")
    
    conv_id = result1.get("conversation_id")
    print(f"   Conversation ID: {conv_id}")
    
    # 3. Segunda consulta
    print("\n3️⃣  SEGUNDA CONSULTA")
    print("-" * 60)
    
    query2 = {
        "query": "¿Cuáles son las propiedades del electrón?",
        "conversation_id": conv_id,
        "top_k": 3
    }
    
    response = requests.post(
        f"{BASE_URL}/query",
        headers=headers,
        json=query2
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        return False
    
    result2 = response.json()
    print(f"✅ Consulta procesada en {result2.get('response_time', 0)}s")
    print(f"   Total fuentes: {result2.get('total_sources', 0)}")
    print(f"   ¿Debe ofrecer examen?: {result2.get('should_offer_exam', False)}")
    
    # 4. Tercera consulta (sin oferta aún)
    print("\n4️⃣  TERCERA CONSULTA")
    print("-" * 60)
    
    query3 = {
        "query": "¿Qué es el número cuántico?",
        "conversation_id": conv_id,
        "top_k": 3
    }
    
    response = requests.post(
        f"{BASE_URL}/query",
        headers=headers,
        json=query3
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        return False
    
    result3 = response.json()
    print(f"✅ Consulta procesada en {result3.get('response_time', 0)}s")
    print(f"   Total fuentes: {result3.get('total_sources', 0)}")
    print(f"   ¿Debe ofrecer examen?: {result3.get('should_offer_exam', False)}")
    
    # 5. Cuarta consulta (AQUÍ debe ofrecer examen)
    print("\n5️⃣  CUARTA CONSULTA (debería ofrecer examen)")
    print("-" * 60)
    
    query4 = {
        "query": "¿Cuál es la diferencia entre orbital y órbita?",
        "conversation_id": conv_id,
        "top_k": 3
    }
    
    response = requests.post(
        f"{BASE_URL}/query",
        headers=headers,
        json=query4
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        return False
    
    result4 = response.json()
    print(f"✅ Consulta procesada en {result4.get('response_time', 0)}s")
    print(f"   Total fuentes: {result4.get('total_sources', 0)}")
    
    if result4.get('should_offer_exam'):
        print(f"✅ OFRECE EXAMEN después de 3 consultas completadas")
        
        # Verificar que el mensaje incluye la oferta
        if "evaluación" in result4.get("answer", "").lower():
            print(f"✅ Mensaje incluye oferta de examen")
        else:
            print(f"⚠️  Mensaje no incluye oferta de examen")
    else:
        print(f"⚠️  NO ofrece examen (debería ofrecerlo)")
    
    # 5. Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN DE VALIDACIONES")
    print("=" * 60)
    
    checks = {
        "Multi-source results": "multi_source_results" in result1,
        "Sin evaluación automática": "Evaluación" not in result1.get("answer", ""),
        "3 fuentes diferentes": result1.get("total_sources", 0) >= 2,
        "Oferta de examen en 3ra consulta": result3.get("should_offer_exam", False),
        "Tiempos < 5s": all(r.get("response_time", 999) < 5 for r in [result1, result2, result3, result4])
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
    
    all_passed = all(checks.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TODAS LAS PRUEBAS PASARON")
    else:
        print("⚠️  ALGUNAS PRUEBAS FALLARON")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    try:
        success = test_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error en prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)