#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   🔍 VERIFICACIÓN SISTEMA V2                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Backend health
echo "1️⃣ Backend health:"
curl -s http://localhost:8000/health | python -m json.tool || echo "   ❌ Backend no responde"

# 2. Frontend
echo ""
echo "2️⃣ Frontend:"
curl -s -I http://localhost:9000 | head -1 || echo "   ❌ Frontend no responde"

# 3. Base de datos
echo ""
echo "3️⃣ Base de datos:"
if [ -f "v2/data/rag_system.db" ]; then
    echo "   ✅ Base de datos existe"
    sqlite3 v2/data/rag_system.db "SELECT COUNT(*) FROM users;" 2>/dev/null && echo "   ✅ Tabla users OK" || echo "   ⚠️ Aún no hay usuarios"
else
    echo "   ⚠️ Base de datos se creará al primer uso"
fi

# 4. Documentos RAG
echo ""
echo "4️⃣ Documentos RAG:"
if [ -d "v2/data/chroma" ]; then
    echo "   ✅ ChromaDB existe"
else
    echo "   ❌ ChromaDB no existe - necesita migrar de v1"
fi

# 5. Procesos
echo ""
echo "5️⃣ Procesos activos:"
ps aux | grep -E "uvicorn.*8000|http.server 9000" | grep -v grep | head -5

echo ""
echo "═══════════════════════════════════════════════"
