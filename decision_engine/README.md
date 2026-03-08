# Verdict Service (Decision Engine)

Production-ready FastAPI microservice for ML-based intrusion detection verdict generation.

## Architecture

```
app/
├── api/
│   ├── routes.py          # API endpoints
│   └── middleware.py      # Error handling
├── services/
│   ├── verdict_service.py      # Core business logic
│   └── severity_strategy.py    # Strategy pattern for severity calculation
├── models/
│   └── schemas.py         # Pydantic models
├── utils/
│   └── logger.py          # Structured logging
├── config.py              # Configuration
└── main.py                # Application factory
```

## Key Design Decisions

1. **Strategy Pattern**: Severity calculation is abstracted into `SeverityStrategy` interface, allowing new scoring algorithms to be plugged in without modifying the controller or service layer.

2. **Dependency Injection**: Config and services are injected via FastAPI's dependency system for testability and flexibility.

3. **Clean Architecture**: Clear separation between API layer, business logic, and data models.

4. **Structured Logging**: JSON logs for easy parsing by log aggregation systems.

5. **Type Safety**: Full type hints and Pydantic validation for runtime safety.

## Quick Start

### Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Docker

```bash
docker build -t verdict-service .
docker run -p 8000:8000 verdict-service
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Example Usage

### Normal Traffic

```bash
curl -X POST http://localhost:8000/api/v1/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "modelFindings": {
      "status": "normal",
      "attack_detected": false,
      "confidence": 0.98,
      "flow_count": 1178
    },
    "context": {
      "networkZone": "Internal",
      "assetCriticality": "High"
    }
  }'
```

**Response:**
```json
{
  "verdict": "LOW",
  "summary": "Normal network behavior detected",
  "explanation": "Traffic analysis shows normal patterns with 98.00% confidence across 1178 flows.",
  "recommendedActions": ["Continue monitoring"],
  "alertsTriggered": []
}
```

### DDoS Attack (Critical)

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

**Response:**
```json
{
  "verdict": "CRITICAL",
  "summary": "DDoS attack detected with CRITICAL severity",
  "explanation": "Attack Type: DDoS | Confidence: 91.00% | Reconstruction Error: 0.870 (threshold: 0.650) | Network Zone: Internal | Asset Criticality: High | Flows Analyzed: 1178 | Final Severity: CRITICAL",
  "recommendedActions": [
    "Enable rate limiting",
    "Block source IPs"
  ],
  "alertsTriggered": ["SOC", "Firewall", "Admin", "SIEM"]
}
```

### Port Scan (Medium)

```bash
curl -X POST http://localhost:8000/api/v1/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "modelFindings": {
      "status": "abnormal",
      "attack_detected": true,
      "attack_type": "PortScan",
      "confidence": 0.78,
      "reconstruction_error": 0.70,
      "threshold": 0.65,
      "flow_count": 450
    },
    "context": {
      "networkZone": "External",
      "assetCriticality": "Low"
    }
  }'
```

**Response:**
```json
{
  "verdict": "MEDIUM",
  "summary": "PortScan attack detected with MEDIUM severity",
  "explanation": "Attack Type: PortScan | Confidence: 78.00% | Reconstruction Error: 0.700 (threshold: 0.650) | Network Zone: External | Asset Criticality: Low | Flows Analyzed: 450 | Final Severity: MEDIUM",
  "recommendedActions": [
    "Monitor source IP",
    "Enable IDS logging"
  ],
  "alertsTriggered": ["SOC"]
}
```

## Health Check

```bash
curl http://localhost:8000/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "verdict-service"
}
```

## Testing

```bash
pytest tests/ -v
```

## Extending Severity Logic

To add a new severity calculation strategy:

```python
from app.services.severity_strategy import SeverityStrategy

class CustomStrategy(SeverityStrategy):
    def calculate(self, findings, context, config):
        # Your custom logic
        return SeverityLevel.HIGH

# Inject in routes.py
def get_verdict_service(cfg: Config = Depends(lambda: config)):
    return VerdictService(cfg, severity_strategy=CustomStrategy())
```

## Configuration

Environment variables (optional `.env` file):

```env
APP_NAME=Verdict Service
VERSION=1.0.0
LOG_LEVEL=INFO
MEDIUM_MULTIPLIER=1.1
HIGH_MULTIPLIER=1.5
CRITICAL_MULTIPLIER=1.5
```

## Production Considerations

- Run behind reverse proxy (nginx/traefik)
- Enable HTTPS/TLS
- Configure rate limiting
- Set up log aggregation (ELK, Datadog)
- Monitor with Prometheus metrics
- Use secrets management for sensitive config
