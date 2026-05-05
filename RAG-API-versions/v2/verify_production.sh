#!/bin/bash

echo "🔍 Verificando Despliegue en Producción"
echo ""

cd /home/medel/BOHR/RAG-API-versions/v2

# 1. Servicios locales
echo "📡 Servicios Locales:"
echo ""

echo "Backend (puerto 8000):"
if curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null; then
    echo "✅ Backend OK"
else
    echo "❌ Backend FAIL"
fi
echo ""

echo "Frontend (puerto 9000):"
if curl -s -I http://localhost:9000 2>/dev/null | head -1 | grep -q "200"; then
    echo "✅ Frontend OK"
else
    echo "❌ Frontend FAIL"
fi
echo ""

# 2. URLs públicas
echo "🌐 URLs Públicas:"
echo ""

echo "Frontend (chat.bohrbot.space):"
if curl -s -I https://chat.bohrbot.space 2>/dev/null | head -1 | grep -q "200"; then
    echo "✅ Accesible"
else
    echo "⚠️  No accesible (puede estar propagando DNS)"
fi
echo ""

echo "Backend API (api.bohrbot.space):"
if curl -s https://api.bohrbot.space/health 2>/dev/null | python -m json.tool 2>/dev/null; then
    echo "✅ API respondiendo"
else
    echo "⚠️  API no accesible"
fi
echo ""

# 3. Verificar procesos
echo "⚙️  Procesos Activos:"
echo ""
ps aux | grep -E "(uvicorn.*8000|http.server 9000|cloudflared tunnel run)" | grep -v grep
echo ""

# 4. Cloudflare Tunnel status
echo "🌐 Estado del Tunnel:"
cloudflared tunnel info bohrbot 2>/dev/null | grep -E "(Name|ID|Created|Connections)" || echo "⚠️  No se pudo obtener info del tunnel"
echo ""

# 5. Logs recientes
if [ -d logs ]; then
    echo "📝 Últimas 5 líneas de logs:"
    echo ""
    
    if [ -f logs/backend_production.log ]; then
        echo "=== Backend ==="
        tail -5 logs/backend_production.log
        echo ""
    fi
    
    if [ -f logs/cloudflare_tunnel.log ]; then
        echo "=== Cloudflare Tunnel ==="
        tail -5 logs/cloudflare_tunnel.log
        echo ""
    fi
fi

echo "✅ Verificación completada"
echo ""