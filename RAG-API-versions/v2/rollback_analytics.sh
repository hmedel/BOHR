#!/bin/bash
echo "🔄 ROLLBACK - Restaurando sistema anterior"

BACKUP_DIR=$(ls -td backups/* | head -1)
echo "Restaurando desde: $BACKUP_DIR"

cp $BACKUP_DIR/main.py.backup app/main.py
cp $BACKUP_DIR/database.py.backup app/database.py
cp $BACKUP_DIR/rag_engine.py.backup app/rag_engine.py
cp $BACKUP_DIR/rag_system.db.backup data/rag_system.db
cp $BACKUP_DIR/.env.backup .env

# Reiniciar backend
sudo pkill -9 -f "uvicorn.*8000"
sleep 5
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > server_rollback.log 2>&1 &

echo "✅ Sistema restaurado - Espera 30 segundos"
sleep 30
curl -s http://localhost:8000/health | python -m json.tool
