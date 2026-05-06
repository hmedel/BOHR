#!/bin/bash
# Loop semanal: backup de DB + rotación de logs
# Ejecutar con: nohup ./backup_loop.sh >> logs/backup.log 2>&1 &
INTERVAL=$((7 * 24 * 3600))  # 7 días
BASEDIR=/home/medel/BOHR/RAG-API-versions/v2
LOGS=$BASEDIR/logs

while true; do
    # Backup de la base de datos
    $BASEDIR/backup_db.sh

    # Rotación del log del backend si supera 5000 líneas (~4 semanas)
    LOG="$LOGS/backend_production.log"
    if [ -f "$LOG" ] && [ "$(wc -l < "$LOG")" -gt 5000 ]; then
        STAMP=$(date +%Y%m%d)
        mv "$LOG" "$LOGS/backend_production_$STAMP.log"
        gzip "$LOGS/backend_production_$STAMP.log"
        touch "$LOG"
        echo "[$(date)] Log rotado → backend_production_$STAMP.log.gz"
        # Conservar solo los últimos 4 archivos rotados
        ls -t "$LOGS"/backend_production_*.log.gz 2>/dev/null | tail -n +5 | xargs -r rm
    fi

    sleep $INTERVAL
done
