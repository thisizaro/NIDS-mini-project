#!/bin/bash
# ML-IDS Pipeline — Stop All Services

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDS_FILE="$PROJECT_DIR/.service_pids"

echo "Stopping ML-IDS services..."

# Stop Docker container
docker rm -f cicflow 2>/dev/null && echo "  Stopped CICFlowMeter (Docker)"

# Stop native processes
if [ -f "$PIDS_FILE" ]; then
    while read entry; do
        if [[ "$entry" == docker:* ]]; then
            continue  # already handled above
        fi
        pid="$entry"
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null && echo "  Stopped PID $pid"
        fi
    done < "$PIDS_FILE"
    rm -f "$PIDS_FILE"
fi

# Kill any remaining processes on our ports
for port in 8010 8001 8002 8003 8080 5173; do
    pid=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null && echo "  Killed process on port $port (PID $pid)"
    fi
done

echo "All services stopped."
