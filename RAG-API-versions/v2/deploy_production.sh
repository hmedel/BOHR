#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   🚀 DESPLIEGUE A PRODUCCIÓN                ║"
echo "║   chat.bohrbot.space                        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

cd /home/medel/BOHR/RAG-API-versions/v2

# 1. Activar entorno
eval "$(conda shell.bash hook)"
conda activate bohrenv

echo "📦 Entorno activado: bohrenv"
echo ""

# 2. Crear directorio de logs
mkdir -p logs

# 3. Detener servicios anteriores
echo "🛑 Deteniendo servicios anteriores..."
pkill -9 -f "uvicorn.*8000" 2>/dev/null
pkill -9 -f "http.server 9000" 2>/dev/null
pkill -9 -f "cloudflared tunnel run" 2>/dev/null
sleep 3
echo "✅ Servicios detenidos"
echo ""

# 4. Iniciar Backend (puerto 8000)
echo "🔧 Iniciando Backend (puerto 8000)..."
nohup python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    > logs/backend_production.log 2>&1 &

BACKEND_PID=$!
echo "✅ Backend iniciado (PID: $BACKEND_PID)"
echo ""

# 5. Iniciar Frontend (puerto 9000)
echo "🌐 Iniciando Frontend (puerto 9000)..."
cd frontend
nohup python -m http.server 9000 > ../logs/frontend_production.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "✅ Frontend iniciado (PID: $FRONTEND_PID)"
echo ""

# 6. Esperar a que servicios estén listos
echo "⏳ Esperando a que servicios estén listos..."
sleep 10

# 7. Verificar servicios locales
echo "🔍 Verificando servicios locales..."
echo ""

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend respondiendo en puerto 8000"
else
    echo "❌ Backend no responde"
    echo "Ver logs: tail -f logs/backend_production.log"
    exit 1
fi

if curl -s http://localhost:9000 > /dev/null 2>&1; then
    echo "✅ Frontend respondiendo en puerto 9000"
else
    echo "❌ Frontend no responde"
    echo "Ver logs: tail -f logs/frontend_production.log"
    exit 1
fi

echo ""

# 8. Verificar configuración de Cloudflare Tunnel
if [ ! -f ~/.cloudflared/config.yml ]; then
    echo "⚠️  ADVERTENCIA: No existe ~/.cloudflared/config.yml"
    echo ""
    echo "Creando configuración básica..."
    
    cat > ~/.cloudflared/config.yml << EOF
tunnel: d72aafcf-191c-4642-be15-83b322945c3d
credentials-file: /home/medel/.cloudflared/d72aafcf-191c-4642-be15-83b322945c3d.json

ingress:
  # Frontend en chat.bohrbot.space
  - hostname: chat.bohrbot.space
    service: http://localhost:9000
  
  # Backend API en api.bohrbot.space
  - hostname: api.bohrbot.space
    service: http://localhost:8000
  
  # Catch-all (obligatorio)
  - service: http_status:404
EOF
    
    echo "✅ Configuración creada"
    echo ""
    echo "📝 IMPORTANTE: Verifica que exista el archivo credentials:"
    echo "   ls -la ~/.cloudflared/d72aafcf-191c-4642-be15-83b322945c3d.json"
    echo ""
fi

# 9. Iniciar Cloudflare Tunnel
echo "🌐 Iniciando Cloudflare Tunnel..."

nohup cloudflared tunnel run bohrbot > logs/cloudflare_tunnel.log 2>&1 &
TUNNEL_PID=$!
echo "✅ Cloudflare Tunnel iniciado (PID: $TUNNEL_PID)"
echo ""

# 10. Esperar a que tunnel se conecte
echo "⏳ Esperando conexión del tunnel (15 segundos)..."
sleep 15

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ DESPLIEGUE COMPLETADO                  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "🌐 URLs de Producción:"
echo "   Frontend: https://chat.bohrbot.space"
echo "   Backend:  https://api.bohrbot.space"
echo "   Health:   https://api.bohrbot.space/health"
echo ""
echo "📊 PIDs de Procesos:"
echo "   Backend:  $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"
echo "   Tunnel:   $TUNNEL_PID"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f logs/backend_production.log"
echo "   Frontend: tail -f logs/frontend_production.log"
echo "   Tunnel:   tail -f logs/cloudflare_tunnel.log"
echo ""
echo "🔍 Verificar estado:"
echo "   ./verify_production.sh"
echo ""
echo "⏳ Nota: La propagación DNS puede tomar 5-10 minutos"
echo ""