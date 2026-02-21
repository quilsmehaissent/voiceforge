#!/bin/bash

# VoiceForge One-Click Launcher
# Usage: ./start.sh [--cpu] [--small]
#   --cpu    : Force usage of CPU (Fixes "channels > 65536" errors on some Macs)
#   --small  : Use smaller 0.6B models (Faster, less RAM)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}      VoiceForge Unified Launcher      ${NC}"
echo -e "${BLUE}=======================================${NC}"

# DIRECTORY SETUP
cd "$(dirname "$0")"

# PARSE ARGUMENTS
export VOICEFORGE_DEVICE=""
export VOICEFORGE_SMALL_MODELS=""

for arg in "$@"
do
    case $arg in
        --cpu)
        echo -e "${BLUE}ℹ️  Mode: FORCE CPU ENABLED (Stability Mode)${NC}"
        export VOICEFORGE_DEVICE="cpu"
        ;;
        --small)
        echo -e "${BLUE}ℹ️  Mode: SMALL MODELS (0.6B) ENABLED (Low RAM Mode)${NC}"
        export VOICEFORGE_SMALL_MODELS="1"
        ;;
    esac
done

# 1. CLEANUP
echo -e "\n${BLUE}[1/3] 🧹 Cleaning up ports 8000 and 3000...${NC}"
PIDS=$(lsof -ti:8000,3000 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    kill -9 $PIDS 2>/dev/null || true
    echo -e "${GREEN}Cleanup complete.${NC}"
else
    echo -e "${GREEN}Ports are already clear.${NC}"
fi

# 2. START BACKEND
echo -e "\n${BLUE}[2/3] 🚀 Starting Backend Server...${NC}"
echo -e "Logs: backend.log"

# Clean log
> backend.log

# Run with environment variables
(cd backend && ./run.sh) > backend.log 2>&1 &
BACKEND_PID=$!

echo -e "${GREEN}Backend started (PID: $BACKEND_PID).${NC}"

# Simple wait loop to check if backend crashes immediately
sleep 5
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}Backend died immediately. Check backend.log:${NC}"
    head -n 20 backend.log
    exit 1
fi

# 3. START FRONTEND
echo -e "\n${BLUE}[3/3] 🌐 Starting Frontend Server...${NC}"
cd frontend || exit 1
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID).${NC}"
echo -e "\n${GREEN}✔ VoiceForge is running!${NC}"
echo -e "  ➜ App:      http://localhost:3000"
echo -e "  ➜ API Docs: http://localhost:8000/docs"

if [ "$VOICEFORGE_DEVICE" == "cpu" ]; then
    echo -e "\n${BLUE}Note: CPU Mode active. Generation will be slower but more stable.${NC}"
fi

echo -e "\n${RED}Press Ctrl+C to stop all servers.${NC}\n"

# CLEANUP FUNCTION
cleanup() {
    echo -e "\n${BLUE}🛑 Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Shutdown complete.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM
wait $FRONTEND_PID $BACKEND_PID
