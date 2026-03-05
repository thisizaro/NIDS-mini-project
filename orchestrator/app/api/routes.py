import io
import json
import logging
import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from app.config import (
    CICFLOWMETER_URL, PREPROCESSOR_URL, MODEL_SERVICE_URL,
    DECISION_ENGINE_URL, REQUEST_TIMEOUT,
)
from app.services.pipeline import run_full_pipeline

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


# ═══════════════════════════════════════════════════════════════
# Full Pipeline
# ═══════════════════════════════════════════════════════════════

@router.post("/pipeline/analyze")
async def analyze_pipeline(
    file: UploadFile = File(...),
    context: str = Form('{"networkZone": "Internal", "assetCriticality": "Medium"}'),
):
    """Run the complete IDS pipeline: PCAP → CICFlowMeter → Preprocess → Model → Verdict."""
    try:
        ctx = json.loads(context)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid context JSON")

    pcap_bytes = await file.read()
    try:
        result = await run_full_pipeline(pcap_bytes, file.filename, ctx)
        return result
    except httpx.HTTPStatusError as e:
        logger.exception("Pipeline step failed")
        raise HTTPException(502, f"Backend service error: {e.response.status_code} - {e.response.text[:500]}")
    except Exception as e:
        logger.exception("Pipeline failed")
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════
# Individual Service Proxies (for testing page)
# ═══════════════════════════════════════════════════════════════

@router.post("/cicflowmeter/process")
async def proxy_cicflowmeter(file: UploadFile = File(...)):
    """Proxy to CICFlowMeter: upload PCAP, get ZIP of CSVs."""
    file_bytes = await file.read()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{CICFLOWMETER_URL}/process",
            files={"file": (file.filename, file_bytes, "application/octet-stream")},
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text[:500])
    return StreamingResponse(
        io.BytesIO(resp.content),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=flows.zip"},
    )


@router.post("/preprocessor/preprocess")
async def proxy_preprocessor(file: UploadFile = File(...)):
    """Proxy to Preprocessor: upload CSV, get scaled features."""
    file_bytes = await file.read()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{PREPROCESSOR_URL}/api/v1/preprocess",
            files={"file": (file.filename, file_bytes, "text/csv")},
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text[:500])
    return resp.json()


@router.post("/model/predict")
async def proxy_model_predict(request: dict):
    """Proxy to Model Service: send features, get predictions."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{MODEL_SERVICE_URL}/api/v1/predict",
            json=request,
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text[:500])
    return resp.json()


@router.post("/model/predict-csv")
async def proxy_model_predict_csv(file: UploadFile = File(...)):
    """Proxy to Model Service: upload CSV, get predictions."""
    file_bytes = await file.read()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{MODEL_SERVICE_URL}/api/v1/predict-csv",
            files={"file": (file.filename, file_bytes, "text/csv")},
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text[:500])
    return resp.json()


@router.post("/decision/verdict")
async def proxy_decision_verdict(request: dict):
    """Proxy to Decision Engine: send findings + context, get verdict."""
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.post(
            f"{DECISION_ENGINE_URL}/api/v1/verdict",
            json=request,
        )
    if resp.status_code != 200:
        raise HTTPException(resp.status_code, resp.text[:500])
    return resp.json()


# ═══════════════════════════════════════════════════════════════
# Aggregated Health
# ═══════════════════════════════════════════════════════════════

@router.get("/health")
async def aggregated_health():
    """Check health of all backend services."""
    services = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        # CICFlowMeter
        try:
            resp = await client.get(f"{CICFLOWMETER_URL}/docs")
            services["cicflowmeter"] = {"status": "healthy" if resp.status_code == 200 else "unhealthy", "port": 8010}
        except Exception:
            services["cicflowmeter"] = {"status": "unhealthy", "port": 8010}

        # Preprocessor
        try:
            resp = await client.get(f"{PREPROCESSOR_URL}/api/v1/health")
            data = resp.json() if resp.status_code == 200 else {}
            services["preprocessor"] = {"status": "healthy", "port": 8001, **data}
        except Exception:
            services["preprocessor"] = {"status": "unhealthy", "port": 8001}

        # Decision Engine
        try:
            resp = await client.get(f"{DECISION_ENGINE_URL}/api/v1/health")
            services["decisionEngine"] = {"status": "healthy", "port": 8002}
        except Exception:
            services["decisionEngine"] = {"status": "unhealthy", "port": 8002}

        # Model Service
        try:
            resp = await client.get(f"{MODEL_SERVICE_URL}/api/v1/health")
            data = resp.json() if resp.status_code == 200 else {}
            services["modelService"] = {"status": "healthy", "port": 8003, **data}
        except Exception:
            services["modelService"] = {"status": "unhealthy", "port": 8003}

    all_healthy = all(s["status"] == "healthy" for s in services.values())
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
    }

# Added per-service timeout and detail to health check
