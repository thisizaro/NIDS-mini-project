from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.utils.logger import setup_logger
from pydantic import ValidationError


logger = setup_logger(__name__)


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    logger.error("Validation error", extra={
        "path": request.url.path,
        "errors": exc.errors()
    })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation failed",
            "errors": exc.errors()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error("Unhandled exception", extra={
        "path": request.url.path,
        "error": str(exc),
        "type": type(exc).__name__
    })
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )
