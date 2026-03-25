#!/bin/bash
# ML-IDS Pipeline — Start All Services
# CICFlowMeter runs in Docker, everything else native
# Usage: bash start_all.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDS_FILE="$PROJECT_DIR/.service_pids"

echo "================================================"
echo "  ML-IDS Pipeline — Starting All Services"
echo "================================================"
echo ""

# Clean up old PID file
> "$PIDS_FILE"

# Step 1: CICFlowMeter in Docker (port 8010 -> container 8000)
echo "[1/6] Starting CICFlowMeter (Docker, port 8010)..."
docker rm -f cicflow 2>/dev/null || true
docker run -d --name cicflow -p 8010:8000 cicflowmeter-api
echo "docker:cicflow" >> "$PIDS_FILE"

# Step 2: Preprocessor Service (port 8001)
echo "[2/6] Starting Preprocessor Service (port 8001)..."
cd "$PROJECT_DIR/preprocessor_module"
python3 -m uvicorn app.main:app --port 8001 --host 0.0.0.0 &
echo $! >> "$PIDS_FILE"

# Step 3: Decision Engine (port 8002)
echo "[3/6] Starting Decision Engine (port 8002)..."
cd "$PROJECT_DIR/decision_engine"
python3 -m uvicorn app.main:app --port 8002 --host 0.0.0.0 &
echo $! >> "$PIDS_FILE"

# Step 4: Model Inference Service (port 8003)
echo "[4/6] Starting Model Service (port 8003)..."
cd "$PROJECT_DIR/model_service"
python3 -m uvicorn app.main:app --port 8003 --host 0.0.0.0 &
echo $! >> "$PIDS_FILE"

# Step 5: Orchestrator (port 8080)
echo "[5/6] Starting Orchestrator (port 8080)..."
cd "$PROJECT_DIR/orchestrator"
python3 -m uvicorn app.main:app --port 8080 --host 0.0.0.0 &
echo $! >> "$PIDS_FILE"

# Step 6: Frontend (port 5173)
echo "[6/6] Starting Frontend (port 5173)..."
cd "$PROJECT_DIR/frontend"
npm run dev &
echo $! >> "$PIDS_FILE"

echo ""
echo "================================================"
echo "  All services started!"
echo "================================================"
echo ""
echo "  Services:"
echo "    CICFlowMeter:   http://localhost:8010  (Docker - real PCAP processing)"
echo "    Preprocessor:    http://localhost:8001  (native)"
echo "    Decision Engine: http://localhost:8002  (native)"
echo "    Model Service:   http://localhost:8003  (native)"
echo "    Orchestrator:    http://localhost:8080  (native)"
echo "    Frontend:        http://localhost:5173  (native)"
echo ""
echo "  Pages:"
echo "    Dashboard:       http://localhost:5173/"
echo "    Analyze:         http://localhost:5173/analyze"
echo "    Service Testing: http://localhost:5173/test"
echo ""
echo "  Stop all: bash stop_all.sh"
echo "================================================"
echo ""

# Wait for all background processes
wait
