#!/bin/bash
set -e

API_URL="http://localhost:8000"

echo "╔══════════════════════════════════════════════╗"
echo "║   📚 CARGAR LIBROS RESTANTES                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Libros restantes (ajustado el nombre)
BOOKS=(
    "/home/medel/BOHR/Books/Atoms_Molecules_and_Photons.md"
    "/home/medel/BOHR/Books/Inorganic_Chemistry_-_James_E_Huheey.md"
    "/home/medel/BOHR/Books/Atomic_Spectra_Atomic_Structure_TRANSLAT.md"
    "/home/medel/BOHR/Books/BransdenJoachain-PhysicsAtomsMolecules.md"
    "/home/medel/BOHR/Books/dokumen.pub_introduction-to-the-structure-of-matter-a-course-in-modern-physics-1nbsped-047160531x.md"
)

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
    
    if [ ! -f "$book" ]; then
        echo "   ❌ Archivo no existe"
        FAILED=$((FAILED+1))
        continue
    fi
    
    size=$(du -h "$book" | cut -f1)
    echo "   Tamaño: $size"
    
    response=$(curl -s -X POST -F "file=@$book" $API_URL/upload 2>&1)
    
    if echo "$response" | grep -q '"status":"success"'; then
        echo "   ✅ Cargado exitosamente"
        SUCCESS=$((SUCCESS+1))
    else
        echo "   ❌ Error al cargar"
        echo "   Respuesta: $(echo $response | head -c 200)"
        FAILED=$((FAILED+1))
    fi
    
    # Tiempo estimado
    ELAPSED=$(($(date +%s) - START_TIME))
    if [ $current -gt 0 ]; then
        AVG_TIME=$((ELAPSED / current))
        REMAINING=$(((TOTAL - current) * AVG_TIME))
        echo "   ⏱️  Tiempo restante: $((REMAINING / 60))m $((REMAINING % 60))s"
    fi
    
    sleep 2
done

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

echo "📚 Todos los documentos en el sistema:"
curl -s $API_URL/documents | python -m json.tool | grep filename | grep -v test

echo ""
echo "✅ Sistema listo"
echo "🌐 Frontend: http://132.248.102.133:9000"
