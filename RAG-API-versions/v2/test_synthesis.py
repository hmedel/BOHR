#!/usr/bin/env python3
"""
Test de la nueva funcionalidad de síntesis con LLM
Verifica que el sistema retorne explicaciones claras en español
"""

import requests
import json

API_URL = "http://localhost:8000"

def test_synthesis():
    print("=" * 70)
    print("🧪 TEST: Síntesis de Respuestas con LLM")
    print("=" * 70)
    
    # Login
    print("\n1️⃣  LOGIN...")
    login_response = requests.post(
        f"{API_URL}/token",
        data={"username": "medel", "password": "admin123"}
    )
    
    if login_response.status_code != 200:
        print(f"   ❌ Error de login: {login_response.status_code}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   ✅ Login exitoso")
    
    # Consulta con síntesis
    print("\n2️⃣  CONSULTA CON SÍNTESIS...")
    print("   Pregunta: '¿Qué es el modelo atómico de Bohr?'")
    
    query_response = requests.post(
        f"{API_URL}/query",
        headers=headers,
        json={
            "query": "¿Qué es el modelo atómico de Bohr?",
            "top_k": 3
        }
    )
    
    if query_response.status_code != 200:
        print(f"   ❌ Error en query: {query_response.status_code}")
        print(f"   Detalle: {query_response.text}")
        return False
    
    data = query_response.json()
    print(f"   ✅ Query exitosa (tiempo: {data.get('response_time', 'N/A')}s)")
    
    # Verificar estructura de respuesta
    print("\n3️⃣  VERIFICAR ESTRUCTURA...")
    
    checks = [
        ("answer" in data, "Campo 'answer'"),
        ("sources" in data, "Campo 'sources'"),
        ("conversation_id" in data, "Campo 'conversation_id'"),
        ("message_id" in data, "Campo 'message_id'"),
    ]
    
    all_passed = True
    for check, desc in checks:
        status = "✅" if check else "❌"
        print(f"   {status} {desc}")
        if not check:
            all_passed = False
    
    if not all_passed:
        print("\n   ❌ Estructura incompleta")
        return False
    
    # Verificar calidad de la respuesta
    print("\n4️⃣  VERIFICAR CALIDAD DE LA SÍNTESIS...")
    
    answer = data["answer"]
    answer_length = len(answer)
    
    print(f"   📏 Longitud de respuesta: {answer_length} caracteres")
    
    # Criterios de calidad
    quality_checks = [
        (answer_length > 500, f"Longitud adecuada (>{500} chars)"),
        ("##" in answer or "**" in answer, "Formato markdown presente"),
        ("Bohr" in answer or "átomo" in answer or "electrón" in answer, "Contenido relevante"),
        (not answer.startswith("🔍"), "NO es formato multi-source crudo"),
        ("Fuente" in answer or "fuente" in answer, "Cita fuentes"),
    ]
    
    quality_passed = True
    for check, desc in quality_checks:
        status = "✅" if check else "⚠️"
        print(f"   {status} {desc}")
        if not check:
            quality_passed = False
    
    # Mostrar primeros 500 caracteres de la respuesta
    print("\n5️⃣  MUESTRA DE LA RESPUESTA SINTETIZADA:")
    print("   " + "─" * 66)
    preview = answer[:500].replace("\n", "\n   ")
    print(f"   {preview}")
    if len(answer) > 500:
        print(f"   ... ({len(answer) - 500} caracteres más)")
    print("   " + "─" * 66)
    
    # Verificar fuentes
    print("\n6️⃣  FUENTES UTILIZADAS:")
    sources = data.get("sources", [])
    print(f"   Total: {len(sources)} fuentes")
    for i, source in enumerate(sources, 1):
        print(f"   {i}. {source}")
    
    # Resultado final
    print("\n" + "=" * 70)
    print("📊 RESULTADO DEL TEST:")
    print("=" * 70)
    
    if all_passed and quality_passed:
        print("✅ Estructura correcta")
        print("✅ Calidad de síntesis adecuada")
        print(f"✅ Respuesta en español con {answer_length} caracteres")
        print(f"✅ {len(sources)} fuentes citadas")
        print("\n🎉 TEST EXITOSO - El sistema sintetiza respuestas claras")
        return True
    else:
        print("❌ Algunos checks fallaron")
        if not all_passed:
            print("   - Estructura incompleta")
        if not quality_passed:
            print("   - Calidad de síntesis insuficiente")
        return False

if __name__ == "__main__":
    try:
        success = test_synthesis()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)