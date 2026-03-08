# Quick Start Guide

## Installation

```bash
# Clone or navigate to project
cd decision_engine

# Install dependencies
pip install -r requirements.txt
```

## Run Locally

```bash
# Start the service
uvicorn app.main:app --reload --port 8000

# In another terminal, test it
./test_requests.sh
```

## Run with Docker

```bash
# Build image
docker build -t verdict-service .

# Run container
docker run -p 8000:8000 verdict-service

# Test
curl http://localhost:8000/api/v1/health
```

## Run Tests

```bash
pytest tests/ -v
```

## API Endpoints

- **POST** `/api/v1/verdict` - Generate verdict
- **GET** `/api/v1/health` - Health check
- **GET** `/docs` - Swagger UI
- **GET** `/redoc` - ReDoc documentation

## Example Request

```bash
curl -X POST http://localhost:8000/api/v1/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "modelFindings": {
      "status": "abnormal",
      "attack_detected": true,
      "attack_type": "DDoS",
      "confidence": 0.91,
      "reconstruction_error": 0.87,
      "threshold": 0.65,
      "flow_count": 1178
    },
    "context": {
      "networkZone": "Internal",
      "assetCriticality": "High"
    }
  }'
```

## Configuration

Create `.env` file (optional):

```env
APP_NAME=Verdict Service
VERSION=1.0.0
LOG_LEVEL=INFO
MEDIUM_MULTIPLIER=1.1
HIGH_MULTIPLIER=1.5
CRITICAL_MULTIPLIER=1.5
```

## Troubleshooting

**Port already in use:**
```bash
uvicorn app.main:app --port 8001
```

**Import errors:**
```bash
# Make sure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Docker build fails:**
```bash
# Check Docker is running
docker ps

# Rebuild without cache
docker build --no-cache -t verdict-service .
```

## Next Steps

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for design details
2. Check [README.md](README.md) for full documentation
3. Explore `/docs` endpoint for interactive API testing
4. Run tests to understand the logic: `pytest tests/ -v`
