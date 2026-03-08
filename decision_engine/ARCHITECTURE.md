# Architecture & Design Decisions

## Overview

The Verdict Service is a production-ready FastAPI microservice that transforms ML detection results into actionable security verdicts. It follows clean architecture principles with clear separation of concerns.

## Core Design Patterns

### 1. Strategy Pattern (Severity Calculation)

**Problem**: Severity calculation logic may evolve over time. Different organizations may want different scoring algorithms.

**Solution**: Abstract severity calculation into a `SeverityStrategy` interface.

```python
class SeverityStrategy(ABC):
    @abstractmethod
    def calculate(self, findings, context, config) -> SeverityLevel:
        pass
```

**Benefits**:
- New algorithms can be added without modifying service or controller code
- Easy to A/B test different strategies
- Testable in isolation
- Follows Open/Closed Principle

**Example Extension**:
```python
class MLBasedStrategy(SeverityStrategy):
    def calculate(self, findings, context, config):
        # Use a trained model to predict severity
        features = self._extract_features(findings, context)
        return self.model.predict(features)
```

### 2. Dependency Injection

**Implementation**: FastAPI's `Depends()` system injects configuration and services.

```python
def get_verdict_service(cfg: Config = Depends(lambda: config)):
    return VerdictService(cfg)
```

**Benefits**:
- Easy to mock dependencies in tests
- Configuration can be swapped without code changes
- Supports multiple environments (dev/staging/prod)

### 3. Clean Architecture Layers

```
┌─────────────────────────────────────┐
│   API Layer (routes.py)             │  ← HTTP concerns
├─────────────────────────────────────┤
│   Service Layer (verdict_service.py)│  ← Business logic
├─────────────────────────────────────┤
│   Strategy Layer (severity_strategy)│  ← Pluggable algorithms
├─────────────────────────────────────┤
│   Models (schemas.py)               │  ← Data contracts
└─────────────────────────────────────┘
```

**Separation of Concerns**:
- **API Layer**: Request validation, HTTP status codes, error responses
- **Service Layer**: Business rules, alert routing, action recommendations
- **Strategy Layer**: Severity calculation algorithms
- **Models**: Type-safe data structures with validation

### 4. Type Safety

**Full type hints** throughout the codebase:
```python
def calculate(
    self, 
    findings: ModelFindingsAbnormal, 
    context: Context, 
    config: Config
) -> SeverityLevel:
```

**Pydantic validation** catches errors at runtime:
- Invalid enum values rejected
- Missing required fields caught
- Type coercion with validation

### 5. Structured Logging

**JSON logs** for machine parsing:
```json
{
  "asctime": "2026-02-26 17:30:45",
  "name": "app.services.verdict_service",
  "levelname": "WARNING",
  "message": "Abnormal traffic detected",
  "attack_type": "DDoS",
  "severity": "CRITICAL",
  "confidence": 0.91
}
```

**Benefits**:
- Easy integration with ELK, Splunk, Datadog
- Structured querying and alerting
- Correlation across microservices

## Decision Logic Flow

```
┌─────────────────┐
│ Receive Request │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ Normal?  │
    └──┬───┬───┘
       │   │
      Yes  No
       │   │
       │   └──► ┌──────────────────────┐
       │        │ Calculate Base       │
       │        │ Severity from Error  │
       │        └──────────┬───────────┘
       │                   │
       │        ┌──────────▼───────────┐
       │        │ Apply Upgrades:      │
       │        │ - High-risk attack   │
       │        │ - Asset criticality  │
       │        │ - Network zone       │
       │        └──────────┬───────────┘
       │                   │
       │        ┌──────────▼───────────┐
       │        │ Map to Alerts        │
       │        │ Get Actions          │
       │        └──────────┬───────────┘
       │                   │
       └───────────────────┴──► Return Verdict
```

## Severity Calculation Algorithm

```python
# Base severity from reconstruction error
if error < threshold * 1.1:  severity = MEDIUM
if error < threshold * 1.5:  severity = HIGH
if error >= threshold * 1.5: severity = CRITICAL

# Upgrade rules (each adds +1 level, capped at CRITICAL)
if attack_type in ["DDoS", "Ransomware"]:  severity += 1
if assetCriticality == "High":             severity += 1
if networkZone == "Internal":              severity += 1
```

**Rationale**:
- **Reconstruction error** indicates anomaly magnitude
- **Attack type** reflects known threat severity
- **Asset criticality** considers business impact
- **Network zone** accounts for exposure risk (internal breaches are worse)

## Alert Routing Matrix

| Severity | Alerts Triggered |
|----------|------------------|
| LOW      | None             |
| MEDIUM   | SOC              |
| HIGH     | SOC + Firewall   |
| CRITICAL | SOC + Firewall + Admin + SIEM |

**Rationale**: Progressive escalation ensures appropriate response without alert fatigue.

## Recommended Actions Mapping

| Attack Type | Actions |
|-------------|---------|
| DDoS        | Enable rate limiting, Block source IPs |
| Ransomware  | Isolate affected host, Disable SMB shares |
| PortScan    | Monitor source IP, Enable IDS logging |
| Default     | Investigate manually, Review logs |

**Extensibility**: Add new attack types to `_get_actions()` method.

## Error Handling Strategy

1. **Validation Errors** (422): Pydantic catches malformed requests
2. **Business Logic Errors** (500): Logged with full context
3. **Unexpected Errors** (500): Caught by global exception handler

All errors produce structured JSON responses with actionable messages.

## Configuration Management

**Environment-based config** via Pydantic Settings:
- Reads from `.env` file or environment variables
- Type-safe with validation
- No hardcoded magic numbers

**Configurable parameters**:
- Severity multipliers (MEDIUM/HIGH/CRITICAL thresholds)
- High-risk attack types list
- Log level

## Testing Strategy

**Unit tests** focus on core logic:
- Severity calculation with various inputs
- Upgrade rules in isolation
- Edge cases (capping at CRITICAL)

**Integration tests** (not included, but recommended):
- Full request/response cycle
- Error handling paths
- Validation edge cases

## Production Readiness Checklist

✅ **Security**:
- Non-root Docker user
- No hardcoded secrets
- Input validation with Pydantic

✅ **Observability**:
- Structured JSON logging
- Health check endpoint
- Docker health check

✅ **Reliability**:
- Type safety throughout
- Comprehensive error handling
- Graceful degradation

✅ **Maintainability**:
- Clean architecture
- Strategy pattern for extensibility
- Clear separation of concerns
- Full type hints

✅ **Deployment**:
- Dockerfile with best practices
- Environment-based configuration
- Ready for container orchestration

## Future Enhancements

1. **Metrics**: Add Prometheus metrics for monitoring
2. **Rate Limiting**: Protect against abuse
3. **Caching**: Cache verdicts for identical inputs
4. **ML-Based Severity**: Train a model to predict severity
5. **Async Processing**: Handle high-volume requests
6. **Database Integration**: Store verdicts for audit trail
7. **Authentication**: Add API key or JWT validation

## Performance Considerations

- **Stateless**: No session state, horizontally scalable
- **Fast**: Pure Python logic, no I/O in critical path
- **Lightweight**: Minimal dependencies, small Docker image
- **Concurrent**: Uvicorn with multiple workers for production

## Deployment Example

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production (4 workers)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Docker
docker build -t verdict-service .
docker run -p 8000:8000 -e LOG_LEVEL=WARNING verdict-service

# Kubernetes (example)
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

## Integration with IDS Pipeline

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────────┐
│   PCAP   │───►│ Preprocessing│───►│  Detection   │───►│ Verdict Service │
│          │    │   Service    │    │   Service    │    │   (This App)    │
└──────────┘    └──────────────┘    └──────────────┘    └────────┬────────┘
                                                                  │
                                                                  ▼
                                                         ┌─────────────────┐
                                                         │  Alert Routing  │
                                                         │  SOC/SIEM/etc   │
                                                         └─────────────────┘
```

**Communication**: REST API with JSON payloads (can be extended to gRPC for performance).

## Summary

This implementation prioritizes:
- **Extensibility**: Strategy pattern allows new algorithms
- **Maintainability**: Clean architecture with clear boundaries
- **Production-readiness**: Error handling, logging, Docker, health checks
- **Type safety**: Full type hints and Pydantic validation
- **Testability**: Dependency injection and isolated business logic

The codebase is ready for production deployment and can scale horizontally to handle high-volume traffic.
