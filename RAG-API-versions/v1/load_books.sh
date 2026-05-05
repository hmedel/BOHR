#!/bin/bash
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   📚 CARGAR LIBROS AL SISTEMA RAG            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Activar ambiente
eval "$(conda shell.bash hook)"
conda activate bohrenv

# API
API_URL="http://localhost:8000"

# Verificar backend
if ! curl -s $API_URL/health > /dev/null; then
    echo "❌ Backend no está corriendo"
    exit 1
fi
echo "✅ Backend activo"
echo ""

# Buscar libros en la ruta específica
BOOKS_PATH="/home/medel/BOHR/Books"
echo "🔍 Buscando archivos .md en $BOOKS_PATH..."

if [ ! -d "$BOOKS_PATH" ]; then
    echo "❌ Directorio no existe: $BOOKS_PATH"
    exit 1
fi

BOOKS=($(find "$BOOKS_PATH" -name "*.md" -type f))

if [ ${#BOOKS[@]} -eq 0 ]; then
    echo "❌ No se encontraron archivos .md en $BOOKS_PATH"
    echo ""
    echo "Archivos en el directorio:"
    ls -lh "$BOOKS_PATH"
    exit 1
fi

echo ""
echo "📚 Encontrados ${#BOOKS[@]} archivos:"
echo ""
for i in "${!BOOKS[@]}"; do
    filename=$(basename "${BOOKS[$i]}")
    size=$(du -h "${BOOKS[$i]}" | cut -f1)
    echo "   $((i+1)). $filename ($size)"
done

echo ""
read -p "¿Cargar todos estos archivos? (y/N): " confirm
if [[ "$confirm" != "y" ]]; then
    echo "Cancelado"
    exit 0
fi

# Cargar cada libro
echo ""
echo "═══════════════════════════════════════════════"
echo "INICIANDO CARGA DE DOCUMENTOS..."
echo "═══════════════════════════════════════════════"
echo ""
echo "⏱️  Tiempo estimado: ~3 minutos por libro"
echo ""

TOTAL=${#BOOKS[@]}
SUCCESS=0
FAILED=0
START_TIME=$(date +%s)

for i in "${!BOOKS[@]}"; do
    book="${BOOKS[$i]}"
    filename=$(basename "$book")
    current=$((i+1))
    
    echo ""
    echo "[$current/$TOTAL] 📖 $filename"
    
    # Upload
    response=$(curl -s -X POST -F "file=@$book" $API_URL/upload 2>&1)
    
    # Verificar resultado
    if echo "$response" | grep -q '"status":"success"'; then
        echo "   ✅ Cargado exitosamente"
        SUCCESS=$((SUCCESS+1))
        
        # Extraer doc_id
        doc_id=$(echo "$response" | grep -o '"doc_id":"[^"]*"' | cut -d'"' -f4)
        echo "   ID: ${doc_id:0:16}..."
    else
        echo "   ❌ Error al cargar"
        FAILED=$((FAILED+1))
        echo "   Respuesta: $(echo $response | head -c 200)"
    fi
    
    # Mostrar progreso
    ELAPSED=$(($(date +%s) - START_TIME))
    AVG_TIME=$((ELAPSED / current))
    REMAINING=$(((TOTAL - current) * AVG_TIME))
    echo "   ⏱️  Tiempo restante estimado: $((REMAINING / 60))m $((REMAINING % 60))s"
    
    # Pausa entre uploads
    sleep 2
done

# Resumen final
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ CARGA COMPLETADA                       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "📊 Resultados:"
echo "   ✅ Exitosos: $SUCCESS"
echo "   ❌ Fallidos:  $FAILED"
echo "   📚 Total:     $TOTAL"
echo "   ⏱️  Tiempo:    $((TOTAL_TIME / 60))m $((TOTAL_TIME % 60))s"
echo ""

# Listar documentos en el sistema
echo "📚 Documentos en el sistema:"
curl -s $API_URL/documents | python -m json.tool

echo ""
echo "🧪 Test de consulta (con los nuevos libros):"
curl -s -X POST $API_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Qué es la estructura atómica?", "top_k": 1, "max_context": 500}' | \
  python -m json.tool | head -25

echo ""
echo ""
echo "✅ Sistema listo para consultas"
echo "🌐 Frontend: http://132.248.102.133:9000"
echo ""
echo "💡 Prueba preguntas como:"
echo "   - ¿Qué es un enlace iónico?"
echo "   - Explica el modelo atómico de Bohr"
echo "   - ¿Qué es el principio de exclusión de Pauli?"
