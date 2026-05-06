#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   📊 ESTADO DEL SISTEMA RAG                 ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Ver qué está corriendo
echo "🔍 Servicios activos:"
ps aux | grep -E "uvicorn.*800|http.server 900" | grep -v grep | while read line; do
    if echo "$line" | grep -q "8001"; then
        echo "   ✅ v1 Backend (puerto 8001)"
    elif echo "$line" | grep -q "8000"; then
        echo "   ✅ v2 Backend (puerto 8000)"
    fi
    if echo "$line" | grep -q "9001"; then
        echo "   ✅ v1 Frontend (puerto 9001)"
    elif echo "$line" | grep -q "9000"; then
        echo "   ✅ v2 Frontend (puerto 9000)"
    fi
done

echo ""
echo "📦 Versiones disponibles:"
ls -d v* 2>/dev/null | while read ver; do
    if [ -f "$ver/VERSION" ]; then
        echo ""
        echo "   📁 $ver:"
        cat "$ver/VERSION" | grep -E "VERSION|DESCRIPTION" | sed 's/^/      /'
    fi
done

echo ""
echo "🔗 URLs de acceso:"
echo "   v1: http://132.248.102.133:8001 (backend) / 9001 (frontend)"
echo "   v2: http://132.248.102.133:8000 (backend) / 9000 (frontend)"
