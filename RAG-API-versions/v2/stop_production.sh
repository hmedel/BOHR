#!/bin/bash

echo "🛑 Deteniendo Servicios de Producción..."
echo ""

# Detener procesos
echo "Deteniendo Backend (puerto 8000)..."
pkill -9 -f "uvicorn.*8000" 2>/dev/null && echo "✅ Backend detenido" || echo "⚠️  Backend no estaba corriendo"

echo "Deteniendo Frontend (puerto 9000)..."
pkill -9 -f "http.server 9000" 2>/dev/null && echo "✅ Frontend detenido" || echo "⚠️  Frontend no estaba corriendo"

echo "Deteniendo Cloudflare Tunnel..."
pkill -9 -f "cloudflared tunnel run" 2>/dev/null && echo "✅ Tunnel detenido" || echo "⚠️  Tunnel no estaba corriendo"

echo ""
echo "✅ Todos los servicios detenidos"
echo ""

# Verificar que no queden procesos
echo "🔍 Verificando procesos restantes..."
REMAINING=$(ps aux | grep -E "(uvicorn.*8000|http.server 9000|cloudflared tunnel run)" | grep -v grep)

if [ -z "$REMAINING" ]; then
    echo "✅ No quedan procesos activos"
else
    echo "⚠️  Procesos que aún están corriendo:"
    echo "$REMAINING"
fi

echo ""