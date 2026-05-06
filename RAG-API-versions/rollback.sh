#!/bin/bash

echo "🚨 ROLLBACK DE EMERGENCIA"
echo ""
echo "Esto detendrá v2 e iniciará v1 inmediatamente"
read -p "¿Continuar? (y/N): " confirm

if [ "$confirm" != "y" ]; then
    echo "Cancelado"
    exit 0
fi

# Detener todo
sudo pkill -9 -f "uvicorn.*800"
sudo pkill -9 -f "http.server 900"
sleep 5

# Activar v1
eval "$(conda shell.bash hook)"
conda activate bohrenv

cd v1
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > server.log 2>&1 &
sleep 20

cd frontend
nohup python -m http.server 9001 > frontend.log 2>&1 &

cd ../..

echo ""
echo "✅ v1 restaurada"
echo "🌐 http://132.248.102.133:9001"
