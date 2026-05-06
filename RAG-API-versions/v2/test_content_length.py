#!/usr/bin/env python3
"""
Prueba rápida: verificar que el contenido retornado sea extenso
"""

import requests
import json

API_URL = "http://localhost:8000"

# Login
login_response = requests.post(
    f"{API_URL}/token",
    data={"username": "medel", "password": "admin123"}
)

if login_response.status_code != 200:
    print(f"❌ Error de login: {login_response.status_code}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Consulta
query_response = requests.post(
    f"{API_URL}/query",
    headers=headers,
    json={
        "query": "¿Qué es el modelo atómico de Bohr?",
        "top_k": 3
    }
)

if query_response.status_code != 200:
    print(f"❌ Error en query: {query_response.status_code}")
    print(query_response.text)
    exit(1)

data = query_response.json()

print("=" * 70)
print("📊 ANÁLISIS DE LONGITUD DE CONTENIDO")
print("=" * 70)

if "multi_source_results" not in data:
    print("❌ No se encontró campo 'multi_source_results'")
    exit(1)

print(f"\n✅ Resultados multi-source: {len(data['multi_source_results'])} fuentes\n")

for result in data["multi_source_results"]:
    content_length = len(result["content"])
    chunks_count = result.get("chunks_count", 1)
    
    print(f"📄 Fuente {result['rank']}: {result['source_display']}")
    print(f"   Chunks combinados: {chunks_count}")
    print(f"   Longitud total: {content_length} caracteres")
    print(f"   Primeras 200 chars: {result['content'][:200]}...")
    
    # Verificar que sea contenido extenso
    if content_length < 1000:
        print(f"   ⚠️  CONTENIDO CORTO (esperado: >1000 chars)")
    else:
        print(f"   ✅ Contenido extenso")
    
    print()

print("=" * 70)
print("🎯 EXPECTATIVA: Cada fuente debería tener ~3000-5000 caracteres")
print("=" * 70)