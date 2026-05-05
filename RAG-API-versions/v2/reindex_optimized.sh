#!/bin/bash
# Script de reindexación optimizada con chunks más grandes
# Fecha: 2025-11-02
# Propósito: Corregir problema de chunks muy pequeños (promedio 101 chars)

set -e

echo "🔄 REINDEXACIÓN OPTIMIZADA DEL VECTOR STORE"
echo "============================================"
echo ""

# Configuración
BACKUP_DIR="./data/backups/$(date +%Y%m%d_%H%M%S)"
CHROMA_PATH="./data/chroma"
UPLOADS_PATH="./data/uploads"

# Paso 1: Backup de la base de datos vectorial actual
echo "📦 Paso 1: Creando backup de ChromaDB actual..."
mkdir -p "$BACKUP_DIR"
if [ -d "$CHROMA_PATH" ]; then
    cp -r "$CHROMA_PATH" "$BACKUP_DIR/chroma_backup"
    echo "   ✅ Backup creado en: $BACKUP_DIR"
else
    echo "   ⚠️  No se encontró ChromaDB existente"
fi

# Paso 2: Eliminar ChromaDB actual
echo ""
echo "🗑️  Paso 2: Eliminando ChromaDB actual..."
if [ -d "$CHROMA_PATH" ]; then
    rm -rf "$CHROMA_PATH"
    echo "   ✅ ChromaDB eliminado"
fi

# Paso 3: Actualizar configuración de chunking
echo ""
echo "⚙️  Paso 3: Verificando configuración de chunking..."
echo "   CHUNK_SIZE actual: $(grep 'CHUNK_SIZE' app/config.py | grep -oP '\d+')"
echo "   CHUNK_OVERLAP actual: $(grep 'CHUNK_OVERLAP' app/config.py | grep -oP '\d+')"
echo ""
echo "   📝 La configuración debería ser:"
echo "      CHUNK_SIZE: 1500 (configurado en config.py)"
echo "      CHUNK_OVERLAP: 300 (configurado en config.py)"

# Paso 4: Reindexar documentos
echo ""
echo "📚 Paso 4: Reindexando documentos principales..."
echo ""

# Contar archivos a procesar
TOTAL_FILES=$(find "$UPLOADS_PATH" -name "*.md" ! -name "test_*" | wc -l)
echo "   Total de archivos a indexar: $TOTAL_FILES"
echo ""

# Ejecutar script Python de reindexación
python3 reindex_documents.py

REINDEX_STATUS=$?

# Paso 5: Verificación
echo ""
echo "🔍 Paso 5: Verificando indexación..."
python3 analyze_vectordb.py | grep -A 5 "TAMAÑO DE CHUNKS"

# Resultado final
echo ""
echo "============================================"
if [ $REINDEX_STATUS -eq 0 ]; then
    echo "✅ REINDEXACIÓN COMPLETADA EXITOSAMENTE"
    echo ""
    echo "📋 Acciones posteriores:"
    echo "   1. Reiniciar servidor: pkill -9 -f uvicorn && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &"
    echo "   2. Probar consulta: '¿Cuál es el Hamiltoniano de H2?'"
    echo "   3. Backup guardado en: $BACKUP_DIR"
else
    echo "❌ ERROR EN LA REINDEXACIÓN"
    echo ""
    echo "🔙 Para restaurar backup:"
    echo "   rm -rf $CHROMA_PATH && cp -r $BACKUP_DIR/chroma_backup $CHROMA_PATH"
fi
echo "============================================"