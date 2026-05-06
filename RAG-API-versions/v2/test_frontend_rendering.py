#!/usr/bin/env python3
"""
Script de prueba para verificar que el frontend muestre correctamente:
1. Nuevas consultas multi-source
2. Conversaciones antiguas cargadas desde la BD
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

def test_complete_flow():
    """Prueba completa: registro, login, consulta nueva, y carga de conversación antigua"""
    
    print("=" * 60)
    print("🧪 TEST: Renderizado Frontend - Consultas Nuevas y Antiguas")
    print("=" * 60)
    
    # 1. Login
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
    
    # 2. Nueva consulta (formato multi-source)
    print("\n2️⃣  NUEVA CONSULTA (formato multi-source)...")
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
    
    query_data = query_response.json()
    print(f"   ✅ Query exitosa")
    
    # Verificar estructura de respuesta nueva
    print("\n   📋 Verificando estructura de respuesta NUEVA:")
    checks = [
        ("answer" in query_data, "Campo 'answer'"),
        ("multi_source_results" in query_data, "Campo 'multi_source_results'"),
        ("total_sources" in query_data, "Campo 'total_sources'"),
        ("conversation_id" in query_data, "Campo 'conversation_id'"),
        ("message_id" in query_data, "Campo 'message_id'"),
        ("response_time" in query_data, "Campo 'response_time'"),
    ]
    
    all_passed = True
    for check, desc in checks:
        status = "✅" if check else "❌"
        print(f"      {status} {desc}")
        if not check:
            all_passed = False
    
    if all_passed:
        print("\n   ✅ Estructura de respuesta NUEVA: CORRECTA")
        
        # Mostrar muestra de multi_source_results
        print("\n   📄 Muestra de multi_source_results:")
        for result in query_data["multi_source_results"][:2]:  # Primeras 2
            print(f"      - Fuente {result['rank']}: {result['source_display']}")
            print(f"        Contenido: {result['content'][:100]}...")
            print(f"        Relevancia: {result['relevance_score']:.2%}")
    else:
        print("\n   ❌ Estructura de respuesta NUEVA: INCOMPLETA")
        return False
    
    conv_id = query_data["conversation_id"]
    
    # 3. Cargar conversación desde BD
    print("\n3️⃣  CARGAR CONVERSACIÓN DESDE BD...")
    time.sleep(1)  # Dar tiempo al backend para guardar
    
    conv_response = requests.get(
        f"{API_URL}/conversations/{conv_id}",
        headers=headers
    )
    
    if conv_response.status_code != 200:
        print(f"   ❌ Error al cargar conversación: {conv_response.status_code}")
        return False
    
    conv_data = conv_response.json()
    print(f"   ✅ Conversación cargada (ID: {conv_id})")
    
    # Verificar estructura de mensajes cargados
    print("\n   📋 Verificando estructura de mensajes ANTIGUOS:")
    
    if "messages" not in conv_data or len(conv_data["messages"]) < 2:
        print("   ❌ No hay suficientes mensajes en la conversación")
        return False
    
    assistant_msg = None
    for msg in conv_data["messages"]:
        if msg["role"] == "assistant":
            assistant_msg = msg
            break
    
    if not assistant_msg:
        print("   ❌ No se encontró mensaje del asistente")
        return False
    
    msg_checks = [
        ("id" in assistant_msg, "Campo 'id'"),
        ("role" in assistant_msg, "Campo 'role'"),
        ("content" in assistant_msg, "Campo 'content'"),
        ("sources" in assistant_msg, "Campo 'sources'"),
        ("created_at" in assistant_msg, "Campo 'created_at'"),
    ]
    
    all_msg_passed = True
    for check, desc in msg_checks:
        status = "✅" if check else "❌"
        print(f"      {status} {desc}")
        if not check:
            all_msg_passed = False
    
    # Verificar contenido del mensaje
    content_length = len(assistant_msg["content"])
    has_content = content_length > 100
    print(f"      {'✅' if has_content else '❌'} Contenido (longitud: {content_length} chars)")
    
    if not has_content:
        print(f"\n      ⚠️  CONTENIDO CORTO:")
        print(f"         {assistant_msg['content'][:200]}")
        all_msg_passed = False
    
    # Verificar fuentes
    sources_count = len(assistant_msg.get("sources", []))
    has_sources = sources_count > 0
    print(f"      {'✅' if has_sources else '⚠️ '} Fuentes ({sources_count} fuentes)")
    
    if has_sources:
        print(f"         Fuentes: {assistant_msg['sources']}")
    
    if all_msg_passed:
        print("\n   ✅ Estructura de mensajes ANTIGUOS: CORRECTA")
    else:
        print("\n   ❌ Estructura de mensajes ANTIGUOS: INCOMPLETA")
        return False
    
    # 4. Resultado final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DEL TEST:")
    print("=" * 60)
    print("✅ Login exitoso")
    print("✅ Nueva consulta (formato multi-source) - Estructura correcta")
    print("✅ Conversación cargada desde BD - Estructura correcta")
    print("✅ Frontend debería renderizar correctamente AMBOS formatos")
    print("\n🎉 TODAS LAS PRUEBAS PASARON")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        success = test_complete_flow()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)