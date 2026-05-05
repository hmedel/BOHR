#!/bin/bash

echo "🔄 Actualizando Backend en Producción..."
echo ""

cd /home/medel/BOHR/RAG-API-versions/v2

# Activar entorno
eval "$(conda shell.bash hook)"
conda activate bohrenv

# Reiniciar solo backend (sin tocar frontend ni tunnel)
echo "🔧 Reiniciando Backend..."
pkill -9 -f "uvicorn.*8000" 2>/dev/null
sleep 3

nohup python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    > logs/backend_production.log 2>&1 &

BACKEND_PID=$!
echo "✅ Backend reiniciado (PID: $BACKEND_PID)"
echo ""

echo "⏳ Esperando 10 segundos..."
sleep 10

# Verificar
echo "🔍 Verificando backend..."
if curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null; then
    echo "✅ Backend respondiendo correctamente"
else
    echo "❌ Backend no responde"
    echo "Ver logs: tail -f logs/backend_production.log"
    exit 1
fi

echo ""
echo "✅ Actualización completada"
echo ""
echo "🌐 Verifica en:"
echo "   Local:      http://localhost:8000/health"
echo "   Producción: https://api.bohrbot.space/health"
echo ""