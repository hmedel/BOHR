#!/bin/bash
# Backup de la base de datos BOHR RAG v2
# Uso manual: ./backup_db.sh
# Uso automático: nohup ./backup_loop.sh &
BACKUP_DIR="/home/medel/BOHR/RAG-API-versions/v2/data/backups"
DB="/home/medel/BOHR/RAG-API-versions/v2/data/rag_system.db"
DEST="$BACKUP_DIR/rag_system_$(date +%Y%m%d_%H%M%S).db"

cp "$DB" "$DEST" && echo "[$(date)] Backup OK: $DEST"

# Conservar solo los últimos 4 backups
ls -t "$BACKUP_DIR"/rag_system_*.db 2>/dev/null | tail -n +5 | xargs -r rm
