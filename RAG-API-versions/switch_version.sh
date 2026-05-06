#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   🔄 CAMBIAR VERSIÓN DEL SISTEMA RAG        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Mostrar versiones disponibles
echo "Versiones disponibles:"
echo ""
echo "1. v1 - Sistema básico (Sin login)"
if [ -f v1/VERSION ]; then
    cat v1/VERSION | grep -E "VERSION|DESCRIPTION"
fi
echo ""
echo "2. v2 - Sistema completo (Con login + historial)"
if [ -f v2/VERSION ]; then
    cat v2/VERSION | grep -E "VERSION|DESCRIPTION"
fi
echo ""

read -p "¿Qué versión quieres activar? (1/2): " VERSION_CHOICE

if [ "$VERSION_CHOICE" == "1" ]; then
    TARGET="v1"
    PORT_BACKEND=8001
    PORT_FRONTEND=9001
elif [ "$VERSION_CHOICE" == "2" ]; then
    TARGET="v2"
    PORT_BACKEND=8000
    PORT_FRONTEND=9000
else
    echo "❌ Opción inválida"
    exit 1
fi

echo ""
echo "🔄 Cambiando a $TARGET..."

# Detener servicios actuales
echo "   Deteniendo servicios..."
sudo pkill -9 -f "uvicorn.*800"
sudo pkill -9 -f "http.server 900"
sleep 5

# Activar ambiente
eval "$(conda shell.bash hook)"
conda activate bohrenv

# Iniciar versión seleccionada
echo "   Iniciando $TARGET..."
cd $TARGET

# Backend
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT_BACKEND > server.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID (puerto $PORT_BACKEND)"

sleep 20

# Frontend
cd frontend 2>/dev/null || mkdir -p frontend
if [ -f index.html ]; then
    nohup python -m http.server $PORT_FRONTEND > frontend.log 2>&1 &
    echo "   Frontend PID: $! (puerto $PORT_FRONTEND)"
fi

cd ../..

echo ""
echo "✅ $TARGET activada"
echo ""
echo "🌐 Accesos:"
echo "   Backend:  http://132.248.102.133:$PORT_BACKEND"
echo "   Frontend: http://132.248.102.133:$PORT_FRONTEND"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f $TARGET/server.log"
echo "   Frontend: tail -f $TARGET/frontend/frontend.log"
