from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import VerdictRequest, VerdictResponse
from app.services.verdict_service import VerdictService
from app.config import Config, config
from app.utils.logger import setup_logger


router = APIRouter()
logger = setup_logger(__name__)


def get_verdict_service(cfg: Config = Depends(lambda: config)) -> VerdictService:
    """Dependency injection for verdict service"""
    return VerdictService(cfg)


@router.post("/verdict", response_model=VerdictResponse, status_code=status.HTTP_200_OK)
async def generate_verdict(
    request: VerdictRequest,
    service: VerdictService = Depends(get_verdict_service)
) -> VerdictResponse:
    """
    Generate security verdict from ML detection results.
    
    Args:
        request: Model findings and context
        service: Injected verdict service
        
    Returns:
        VerdictResponse with severity, explanation, and actions
    """
    try:
        logger.info("Verdict request received", extra={
            "status": request.modelFindings.get("status"),
            "network_zone": request.context.networkZone.value
        })
        
        verdict = service.generate_verdict(request)
        
        logger.info("Verdict generated", extra={
            "verdict": verdict.verdict.value,
            "alerts": [a.value for a in verdict.alertsTriggered]
        })
        
        return verdict
        
    except Exception as e:
        logger.error("Verdict generation failed", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verdict generation failed: {str(e)}"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "verdict-service"}
