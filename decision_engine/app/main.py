from fastapi import FastAPI
from pydantic import ValidationError
from app.api.routes import router
from app.api.middleware import validation_exception_handler, generic_exception_handler
from app.config import config
from app.utils.logger import setup_logger


logger = setup_logger(__name__, config.LOG_LEVEL)


def create_app() -> FastAPI:
    """Application factory"""
    app = FastAPI(
        title=config.APP_NAME,
        version=config.VERSION,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Register exception handlers
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    # Register routes
    app.include_router(router, prefix="/api/v1")
    
    logger.info("Application started", extra={
        "app_name": config.APP_NAME,
        "version": config.VERSION
    })
    
    return app


app = create_app()
