#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   🧪 TEST COMPLETO DEL SISTEMA              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Backend
echo "1️⃣ Backend v2:"
curl -s http://localhost:8000/health | python -m json.tool

# 2. Frontend
echo ""
echo "2️⃣ Frontend v2:"
curl -s -I http://localhost:9000 | head -1

# 3. Documentos
echo ""
echo "3️⃣ Documentos cargados:"
curl -s http://localhost:8000/documents -H "Authorization: Bearer fake" 2>/dev/null | grep -o '"filename":[^,]*' | head -10 || echo "   (Requiere login)"

# 4. Base de datos
echo ""
echo "4️⃣ Base de datos:"
sqlite3 v2/data/rag_system.db "SELECT COUNT(*) || ' usuarios' FROM users; SELECT COUNT(*) || ' conversaciones' FROM conversations; SELECT COUNT(*) || ' mensajes' FROM messages;" 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════"
echo ""
echo "🌐 URLs:"
echo "   Frontend: http://132.248.102.133:9000"
echo "   API Docs: http://132.248.102.133:8000/docs"
echo ""
echo "📝 Logs:"
echo "   tail -f v2/server_multi.log"
echo "   tail -f v2/frontend/frontend.log"
