#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   📦 MIGRAR DATOS DE v1 A v2                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

read -p "¿Migrar documentos RAG de v1 a v2? (y/N): " confirm

if [ "$confirm" != "y" ]; then
    echo "Cancelado"
    exit 0
fi

echo ""
echo "Copiando ChromaDB..."
if [ -d "v1/data/chroma" ]; then
    cp -r v1/data/chroma v2/data/
    echo "   ✅ ChromaDB migrada"
else
    echo "   ❌ No hay ChromaDB en v1"
fi

echo ""
echo "Copiando uploads..."
if [ -d "v1/data/uploads" ]; then
    mkdir -p v2/data/uploads
    cp -r v1/data/uploads/* v2/data/uploads/ 2>/dev/null
    echo "   ✅ Uploads migrados"
fi

echo ""
echo "✅ Migración completada"
echo ""
echo "🔄 Reinicia v2 para aplicar cambios:"
echo "   ./switch_version.sh"
