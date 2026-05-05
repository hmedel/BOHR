#!/bin/bash
# Startup script for RAG-API v2 System
# Created: 2025-10-26

echo "🚀 Starting RAG-API v2 System..."
echo "================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=9000
BASE_DIR="$HOME/BOHR/RAG-API-versions/v2"

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Killing processes on port $port: $pids${NC}"
        kill -9 $pids 2>/dev/null
        sleep 1
    fi
}

# Check and stop existing services
echo -e "${YELLOW}Checking for existing services...${NC}"
if check_port $BACKEND_PORT; then
    echo "Found service on port $BACKEND_PORT"
    kill_port $BACKEND_PORT
fi
if check_port $FRONTEND_PORT; then
    echo "Found service on port $FRONTEND_PORT"
    kill_port $FRONTEND_PORT
fi

# Start backend
echo -e "${GREEN}Starting backend on port $BACKEND_PORT...${NC}"
cd "$BASE_DIR"

# Activate conda environment and start backend
eval "$(conda shell.bash hook)"
conda activate bohrenv 2>/dev/null || {
    echo -e "${RED}Error: bohrenv conda environment not found${NC}"
    echo "Please create it with: conda create -n bohrenv python=3.12"
    exit 1
}

nohup python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $BACKEND_PORT \
    --reload \
    > server.log 2>&1 &

BACKEND_PID=$!
echo -e "${GREEN}Backend started with PID: $BACKEND_PID${NC}"

# Wait for backend to be ready
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready!${NC}"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}Backend failed to start. Check server.log for errors.${NC}"
        exit 1
    fi
done

# Start frontend
echo -e "${GREEN}Starting frontend on port $FRONTEND_PORT...${NC}"
cd "$BASE_DIR/frontend"
nohup python -m http.server $FRONTEND_PORT --bind 0.0.0.0 > frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started with PID: $FRONTEND_PID${NC}"

# Get system IP
IP=$(hostname -I | awk '{print $1}')

# Display access information
echo ""
echo "================================"
echo -e "${GREEN}✅ System Successfully Started!${NC}"
echo "================================"
echo ""
echo "📍 Access URLs:"
echo "   Local:    http://localhost:$FRONTEND_PORT"
echo "   Network:  http://$IP:$FRONTEND_PORT"
echo ""
echo "🔑 Test Account:"
echo "   Username: demo"
echo "   Password: demo123"
echo ""
echo "📊 Service Status:"
echo "   Backend:  http://localhost:$BACKEND_PORT/health"
echo "   Frontend: http://localhost:$FRONTEND_PORT"
echo "   API Docs: http://localhost:$BACKEND_PORT/docs"
echo ""
echo "📝 Logs:"
echo "   Backend:  $BASE_DIR/server.log"
echo "   Frontend: $BASE_DIR/frontend/frontend.log"
echo ""
echo "🛑 To stop services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "⚠️  Security Warning:"
echo "   The DeepSeek API key in .env needs to be regenerated!"
echo "   Current key is exposed and should not be used in production."
echo ""

# Save PIDs to file for easy stopping
echo "$BACKEND_PID" > /tmp/rag_v2_backend.pid
echo "$FRONTEND_PID" > /tmp/rag_v2_frontend.pid

echo "PIDs saved to /tmp/rag_v2_*.pid for reference"
echo ""