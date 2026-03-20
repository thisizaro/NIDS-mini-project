from fastapi import FastAPI
from pydantic import ValidationError

from app.api.routes import router
from app.config import config
from app.utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL)


def validation_exception_handler(request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


def generic_exception_handler(request, exc):
    from fastapi.responses import JSONResponse

    logger.error("Unhandled exception", extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title=config.APP_NAME,
        version=config.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(router, prefix="/api/v1")

    logger.info(
        "Application started",
        extra={"app_name": config.APP_NAME, "version": config.VERSION},
    )

    return app


app = create_app()

# # Added CORS middleware
