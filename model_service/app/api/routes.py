import logging
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from app.services.inference import get_inference_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


class PredictRequest(BaseModel):
    features: List[List[float]]
    feature_names: List[str]


@router.post("/predict")
async def predict_from_features(request: PredictRequest):
    """Predict from preprocessor output (feature arrays + names)."""
    svc = get_inference_service()
    try:
        result = svc.predict_from_features(request.features, request.feature_names)
        return result
    except Exception as e:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-csv")
async def predict_from_csv(file: UploadFile = File(...)):
    """Predict from raw CICFlowMeter CSV file."""
    svc = get_inference_service()
    try:
        csv_bytes = await file.read()
        result = svc.predict_from_csv(csv_bytes)
        return result
    except Exception as e:
        logger.exception("CSV prediction failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health():
    svc = get_inference_service()
    return {
        "status": "healthy" if svc.is_loaded else "loading",
        "model_loaded": svc.model is not None,
        "scaler_loaded": svc.scaler is not None,
        "openmax_loaded": svc.openmax_mavs is not None,
        "feature_cols": len(svc.feature_cols) if svc.feature_cols else 0,
    }
