"""FastAPI application factory."""

from fastapi import FastAPI

from content_os.api.health import router as health_router
from content_os.api.workflows import router as workflow_router
from content_os.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.app_environment != "production" else None,
        redoc_url=None,
    )
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(workflow_router, prefix="/api/v1")
    return application


app = create_app()
