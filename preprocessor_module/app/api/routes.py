from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import Config, config
from app.models.schemas import HealthResponse, PreprocessResponse
from app.services.preprocessor import PreprocessorService
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

_service: PreprocessorService | None = None


def get_preprocessor_service(
    cfg: Config = Depends(lambda: config),
) -> PreprocessorService:
    global _service
    if _service is None:
        _service = PreprocessorService(cfg)
    return _service


@router.post(
    "/preprocess",
    response_model=PreprocessResponse,
    status_code=status.HTTP_200_OK,
)
async def preprocess_csv(
    file: UploadFile = File(...),
    service: PreprocessorService = Depends(get_preprocessor_service),
) -> PreprocessResponse:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are accepted",
        )

    try:
        csv_bytes = await file.read()
        result = service.preprocess(csv_bytes)
        logger.info(
            "Preprocess request completed",
            extra={"csv_filename": file.filename, "rows": result["row_count"]},
        )
        return PreprocessResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        logger.error("Preprocessing failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Preprocessing failed: {str(e)}",
        )


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    scaler_loaded = _service is not None and _service.scaler is not None
    return HealthResponse(
        status="healthy",
        service="preprocessor-service",
        scaler_loaded=scaler_loaded,
    )
