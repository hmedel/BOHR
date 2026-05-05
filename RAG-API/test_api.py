#!/usr/bin/env python
"""Script para probar el API sin autenticación"""

import requests
import json

API_URL = "http://localhost:8000"

def test_health():
    """Probar health endpoint"""
    print("🔍 Probando health check...")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def register_user():
    """Registrar usuario de prueba"""
    print("\n📝 Registrando usuario de prueba...")
    user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "test123"
    }
    response = requests.post(f"{API_URL}/register", json=user_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Usuario registrado exitosamente")
    else:
        print(f"Response: {response.text}")
    return response.status_code == 200

def get_token():
    """Obtener token de autenticación"""
    print("\n🔑 Obteniendo token...")
    login_data = {
        "username": "test_user",
        "password": "test123"
    }
    response = requests.post(
        f"{API_URL}/token",
        data=login_data
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Token obtenido: {token[:20]}...")
        return token
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_query_with_auth(token):
    """Probar query con autenticación"""
    print("\n📊 Probando query con autenticación...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    query_data = {
        "query": "¿Qué es un átomo?",
        "top_k": 1,
        "max_context": 500
    }
    response = requests.post(
        f"{API_URL}/query",
        headers=headers,
        json=query_data
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Respuesta: {result['answer'][:100]}...")
    else:
        print(f"❌ Error: {response.text}")
    return response.status_code == 200

def main():
    print("=" * 50)
    print("🧪 PRUEBA DE API RAG")
    print("=" * 50)
    
    # Test health
    if not test_health():
        print("❌ Backend no está respondiendo")
        return
    
    # Register user
    register_user()  # Puede fallar si ya existe
    
    # Get token
    token = get_token()
    if not token:
        print("❌ No se pudo obtener token")
        return
    
    # Test query
    test_query_with_auth(token)
    
    print("\n" + "=" * 50)
    print("✅ Pruebas completadas")
    print("\nPuedes usar este token en las llamadas API:")
    print(f"Authorization: Bearer {token}")
    
if __name__ == "__main__":
    main()