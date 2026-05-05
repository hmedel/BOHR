#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   🔍 TEST COMPLETO DEL SISTEMA               ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Backend
echo "1️⃣ Backend (puerto 8000):"
curl -s http://132.248.102.133:8000/health && echo " ✅ OK" || echo " ❌ Error"

# 2. Frontend
echo ""
echo "2️⃣ Frontend (puerto 9000):"
curl -s -I http://132.248.102.133:9000 | head -1

# 3. Query test
echo ""
echo "3️⃣ Query test:"
RESPONSE=$(curl -s -X POST http://132.248.102.133:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}')
echo "$RESPONSE" | python -m json.tool | head -10

# 4. Procesos
echo ""
echo "4️⃣ Procesos activos:"
ps aux | grep -E "uvicorn|http.server" | grep -v grep

# 5. Puertos
echo ""
echo "5️⃣ Puertos:"
sudo ss -tlnp | grep -E ":8000|:9000"

echo ""
echo "═══════════════════════════════════════════════"
