#!/bin/bash
set -e

echo "🔧 Reiniciando Open WebUI con configuración limpia"
echo ""

# Paso 1: Detener y eliminar contenedor
echo "1️⃣ Deteniendo contenedor..."
docker stop open-webui 2>/dev/null || true
docker rm open-webui 2>/dev/null || true

# Paso 2: Eliminar base de datos vieja
echo ""
echo "2️⃣ Eliminando base de datos con chunks viejos..."
docker run --rm -v open-webui:/data alpine sh -c "
  rm -f /data/webui.db
  rm -f /data/webui.db-shm
  rm -f /data/webui.db-wal
  echo '✅ Base de datos eliminada'
"

# Paso 3: Crear contenedor nuevo
echo ""
echo "3️⃣ Creando contenedor con configuración optimizada..."
docker run -d --network=host \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
  -e WEBUI_AUTH=True \
  -e ENABLE_SIGNUP=False \
  -e CHUNK_SIZE=150 \
  -e CHUNK_OVERLAP=15 \
  -e RAG_TOP_K=1 \
  -e RAG_RELEVANCE_THRESHOLD=0.80 \
  -e ENABLE_RAG_HYBRID_SEARCH=false \
  -e RAG_EMBEDDING_ENGINE=ollama \
  -e RAG_EMBEDDING_MODEL=nomic-embed-text:latest \
  -e RAG_EMBEDDING_BATCH_SIZE=10 \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart=always \
  ghcr.io/open-webui/open-webui:main

echo ""
echo "⏳ Esperando 40 segundos para que inicie..."
sleep 40

# Paso 4: Verificar
echo ""
echo "4️⃣ Verificando..."
if docker ps | grep -q open-webui; then
    echo "✅ Open WebUI corriendo"
    docker logs open-webui --tail 10
else
    echo "❌ Error al iniciar"
    docker logs open-webui --tail 30
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     ✅ SISTEMA LIMPIO Y CONFIGURADO         ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "🌐 URL: http://localhost:8080"
echo ""
echo "📝 IMPORTANTE:"
echo "  - Tendrás que crear usuario NUEVO"
echo "  - Y re-subir los 8 libros UNO POR UNO"
echo ""
echo "⚙️ Configuración RAG:"
echo "  - Chunks: 150 palabras (~195 tokens)"
echo "  - Top K: 1 (solo el mejor chunk)"
echo "  - Tokens por query: ~500"
echo "  - Límite DeepSeek: 131,072"
echo "  - Uso: 0.38% del límite ✓"
echo ""
echo "🔧 Comandos útiles:"
echo "  docker logs -f open-webui"
echo "  watch -n 1 nvidia-smi"
echo ""
