"""Main FastAPI application."""
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health_router, requests_router
from app.core.config import settings
from app.core.database import init_db
from app.services.fetcher import close_fetcher
from app.services.seeder import shutdown_seeder
from app.tasks.queue import get_task_queue

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.monitoring.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Starting ProxyTorrent service")

    # Initialize storage
    settings.initialize_storage()
    logger.info("Storage initialized")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Start task queue
    task_queue = get_task_queue()
    await task_queue.start()
    logger.info("Task queue started")

    yield

    # Shutdown
    logger.info("Shutting down ProxyTorrent service")

    # Stop task queue
    await task_queue.stop()
    logger.info("Task queue stopped")

    # Shutdown seeder
    shutdown_seeder()
    logger.info("Seeder stopped")

    # Close fetcher
    await close_fetcher()
    logger.info("Fetcher closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Combined Proxy + BitTorrent service for secure content fetching and distribution",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(requests_router, prefix=settings.api_prefix)

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": f"{settings.api_prefix}/docs",
        }

    return app


app = create_app()
