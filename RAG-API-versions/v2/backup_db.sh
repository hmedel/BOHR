#!/bin/bash
# Backup semanal de la base de datos BOHR RAG v2
# Uso: ./backup_db.sh  (o programar con at/systemd/screen)
BACKUP_DIR="/home/medel/BOHR/RAG-API-versions/v2/data/backups"
DB="/home/medel/BOHR/RAG-API-versions/v2/data/rag_system.db"
DEST="$BACKUP_DIR/rag_system_$(date +%Y%m%d_%H%M%S).db"

cp "$DB" "$DEST" && echo "Backup OK: $DEST"

# Conservar solo los últimos 4 backups
ls -t "$BACKUP_DIR"/rag_system_*.db | tail -n +5 | xargs -r rm && echo "Backups antiguos limpiados"
