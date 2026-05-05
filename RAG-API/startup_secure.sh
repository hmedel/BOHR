#!/bin/bash

# Startup script with security checks
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║   🚀 RAG-API SECURE STARTUP                  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo "🔍 Checking dependencies..."
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3 found${NC}"

# Check Ollama
if ! command_exists ollama; then
    echo -e "${YELLOW}⚠️  Ollama not found. Please install: https://ollama.ai${NC}"
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Ollama is not running. Starting...${NC}"
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi
echo -e "${GREEN}✅ Ollama is running${NC}"

# Check for nomic-embed-text model
if ! ollama list | grep -q "nomic-embed-text"; then
    echo -e "${YELLOW}⚠️  nomic-embed-text model not found. Pulling...${NC}"
    ollama pull nomic-embed-text:latest
fi
echo -e "${GREEN}✅ Embeddings model ready${NC}"

# Check .env file
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo ""
    echo "Please create .env file from .env.example:"
    echo "  cp .env.example .env"
    echo "  # Edit .env and add your API keys"
    exit 1
fi

# Validate .env has required keys
if ! grep -q "DEEPSEEK_API_KEY=sk-" .env || grep -q "DEEPSEEK_API_KEY=sk-CHANGE" .env; then
    echo -e "${RED}❌ DEEPSEEK_API_KEY not configured in .env${NC}"
    echo "Please add your DeepSeek API key to .env"
    exit 1
fi

if ! grep -q "JWT_SECRET=" .env || grep -q "JWT_SECRET=CHANGE" .env; then
    echo -e "${YELLOW}⚠️  JWT_SECRET not configured. Generating...${NC}"
    JWT_SECRET=$(openssl rand -hex 32)
    echo "" >> .env
    echo "# Auto-generated JWT secret" >> .env
    echo "JWT_SECRET=$JWT_SECRET" >> .env
    echo -e "${GREEN}✅ JWT secret generated${NC}"
fi

echo ""
echo "🔒 Security checks passed!"
echo ""

# Create/activate virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Create necessary directories
mkdir -p data/chroma data/uploads logs

# Database initialization
echo "🗄️ Initializing database..."
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)" 2>/dev/null || true

# Kill any existing processes on ports
echo "🔄 Checking ports..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 9000/tcp 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   🚀 STARTING SERVICES                       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Start backend
echo "🔧 Starting backend on port 8000..."
nohup python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"

# Start frontend
echo "🌐 Starting frontend on port 9000..."
cd frontend
nohup python -m http.server 9000 > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "   PID: $FRONTEND_PID"

# Wait for services to start
echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Health check
echo ""
echo "🔍 Running health checks..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend is healthy${NC}"
else
    echo -e "${RED}❌ Backend failed to start. Check logs/backend.log${NC}"
    exit 1
fi

if curl -s -I http://localhost:9000 | head -1 | grep -q "200"; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${RED}❌ Frontend failed to start. Check logs/frontend.log${NC}"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   ✅ SISTEMA INICIADO CORRECTAMENTE          ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "📊 Services:"
echo "   🔧 Backend:  http://localhost:8000"
echo "   🌐 Frontend: http://localhost:9000"
echo "   📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   tail -f logs/backend.log"
echo "   tail -f logs/frontend.log"
echo ""
echo "🛑 To stop services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   # or use: pkill -f uvicorn"
echo ""
echo "⚠️  IMPORTANT: First time users should:"
echo "   1. Register at http://localhost:9000"
echo "   2. Load documents with: ./load_books.sh"
echo ""