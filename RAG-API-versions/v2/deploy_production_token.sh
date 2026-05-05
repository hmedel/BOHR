#!/bin/bash

# Script de despliegue a producción usando token de Cloudflare Tunnel
# Este script NO requiere el archivo de credenciales JSON

set -e  # Exit on error

echo "========================================"
echo "🚀 Despliegue a Producción - RAG v2"
echo "========================================"
echo ""

# Configuración
BACKEND_PORT=8000
FRONTEND_PORT=9000
TUNNEL_TOKEN="eyJhIjoiOTNmZTQ2Mjg2M2U2MDIwNTM0YzJkYzg5M2E0NmQzZDYiLCJzIjoiY3F2bFVuakNuZkNWZm8xRFF1T2lUc2dKb0xqSjVRZHRvQXlZRUF1N25Odz0iLCJ0IjoiZDcyYWFmY2YtMTkxYy00NjQyLWJlMTUtODNiMzIyOTQ1YzNkIn0="

# Crear directorio de logs si no existe
mkdir -p logs

echo "🛑 Deteniendo servicios anteriores..."
echo ""

# Detener procesos anteriores
pkill -f "uvicorn app.main:app" || true
pkill -f "python -m http.server $FRONTEND_PORT" || true
pkill -f "cloudflared tunnel" || true

sleep 2

echo "✅ Servicios anteriores detenidos"
echo ""

# Verificar que conda está disponible
if ! command -v conda &> /dev/null; then
    echo "❌ Error: conda no está disponible"
    exit 1
fi

# Activar entorno conda
echo "🔧 Activando entorno bohrenv..."
eval "$(conda shell.bash hook)"
conda activate bohrenv

echo "✅ Entorno activado"
echo ""

# Iniciar backend
echo "🚀 Iniciando backend en puerto $BACKEND_PORT..."
nohup python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $BACKEND_PORT \
    --workers 12 \
    --log-level info \
    > logs/backend_production.log 2>&1 &

BACKEND_PID=$!
echo "✅ Backend iniciado (PID: $BACKEND_PID)"
echo ""

# Esperar a que el backend esté listo
echo "⏳ Esperando a que el backend esté listo..."
sleep 5

# Verificar backend
if curl -s http://localhost:$BACKEND_PORT/health > /dev/null; then
    echo "✅ Backend funcionando correctamente"
else
    echo "⚠️  Backend no responde, revisa logs/backend_production.log"
fi
echo ""

# Iniciar frontend
echo "🚀 Iniciando frontend en puerto $FRONTEND_PORT..."
cd frontend
nohup python -m http.server $FRONTEND_PORT > ../logs/frontend_production.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "✅ Frontend iniciado (PID: $FRONTEND_PID)"
echo ""

# Esperar a que el frontend esté listo
echo "⏳ Esperando a que el frontend esté listo..."
sleep 3

# Verificar frontend
if curl -s http://localhost:$FRONTEND_PORT > /dev/null; then
    echo "✅ Frontend funcionando correctamente"
else
    echo "⚠️  Frontend no responde, revisa logs/frontend_production.log"
fi
echo ""

# Iniciar Cloudflare Tunnel con token
echo "🌐 Iniciando Cloudflare Tunnel..."
nohup cloudflared tunnel run --token $TUNNEL_TOKEN > logs/cloudflare_tunnel.log 2>&1 &
TUNNEL_PID=$!

echo "✅ Cloudflare Tunnel iniciado (PID: $TUNNEL_PID)"
echo ""

# Esperar a que el tunnel conecte
echo "⏳ Esperando a que el tunnel conecte..."
sleep 5

echo ""
echo "========================================"
echo "✅ DESPLIEGUE COMPLETADO"
echo "========================================"
echo ""
echo "📊 Estado de los servicios:"
echo ""
echo "  Backend:  http://localhost:$BACKEND_PORT (PID: $BACKEND_PID)"
echo "  Frontend: http://localhost:$FRONTEND_PORT (PID: $FRONTEND_PID)"
echo "  Tunnel:   Cloudflare (PID: $TUNNEL_PID)"
echo ""
echo "🌐 URLs públicas:"
echo ""
echo "  Frontend: https://chat.bohrbot.space"
echo "  API:      https://api.bohrbot.space"
echo "  Health:   https://api.bohrbot.space/health"
echo ""
echo "📝 Logs disponibles en:"
echo ""
echo "  Backend:  tail -f logs/backend_production.log"
echo "  Frontend: tail -f logs/frontend_production.log"
echo "  Tunnel:   tail -f logs/cloudflare_tunnel.log"
echo ""
echo "🔍 Verificar servicios:"
echo ""
echo "  ./verify_production.sh"
echo ""
echo "🛑 Detener servicios:"
echo ""
echo "  ./stop_production.sh"
echo ""
echo "========================================"
echo "⏳ Esperando propagación DNS (puede tomar 2-5 minutos)..."
echo "========================================"
echo ""