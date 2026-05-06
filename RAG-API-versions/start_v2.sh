#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   🚀 INICIANDO SISTEMA V2                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd /home/medel/BOHR/RAG-API-versions/v2

eval "$(conda shell.bash hook)"
conda activate bohrenv

# Limpiar cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Iniciar backend
echo "1️⃣ Iniciando backend v2 (puerto 8000)..."
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > server.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

echo "   Esperando 30 segundos..."
sleep 30

# Verificar backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✅ Backend OK"
else
    echo "   ❌ Backend falló. Ver logs:"
    tail -30 server.log
    exit 1
fi

# Iniciar frontend
echo ""
echo "2️⃣ Iniciando frontend v2 (puerto 9000)..."
cd frontend
nohup python -m http.server 9000 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

sleep 5

if curl -s http://localhost:9000 > /dev/null; then
    echo "   ✅ Frontend OK"
else
    echo "   ❌ Frontend falló"
    exit 1
fi

cd ../..

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ SISTEMA V2 INICIADO                    ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "🌐 Accesos:"
echo "   Frontend: http://132.248.102.133:9000"
echo "   Backend:  http://132.248.102.133:8000"
echo "   API Docs: http://132.248.102.133:8000/docs"
echo ""
echo "📚 Características:"
echo "   ✅ Sistema de login multiusuario"
echo "   ✅ Historial persistente por usuario"
echo "   ✅ Colores UNAM (azul y oro)"
echo "   ✅ Markdown con fórmulas matemáticas"
echo "   ✅ 7 libros de química cargados"
echo ""
echo "👤 Para crear tu primer usuario:"
echo "   1. Abre: http://132.248.102.133:9000"
echo "   2. Haz clic en 'Regístrate aquí'"
echo "   3. Completa el formulario"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f v2/server.log"
echo "   Frontend: tail -f v2/frontend/frontend.log"
echo ""
echo "🔄 Para volver a v1:"
echo "   ./rollback.sh"
