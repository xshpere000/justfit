"""FastAPI Application Entry Point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import sys
import traceback

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.config import settings
from app.core.database import engine, Base
from app.core.logging import setup_logging
from app.routers import connection, task, resource, analysis, report


setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    logger.info("application_starting", version="0.0.3")
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("lifespan_shutdown", reason="Application lifespan ending")
    logger.info("application_shutting_down", reason="Lifespan context exit")
    # Close database connection
    try:
        await engine.dispose()
        logger.info("database_closed", status="success")
    except Exception as e:
        logger.error("database_close_error", error=str(e))


app = FastAPI(
    title="JustFit API",
    description="Cloud Platform Resource Assessment Tool",
    version="0.0.3",
    lifespan=lifespan,
)

# CORS middleware - Allow local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(connection.router, prefix="/api/connections", tags=["connections"])
app.include_router(task.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(resource.router, prefix="/api/resources", tags=["resources"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(report.router, prefix="/api/reports", tags=["reports"])


# Global exception handler to prevent crashes
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch unhandled exceptions."""
    exc_type = type(exc).__name__
    exc_traceback = traceback.format_exc()

    logger.error(
        "unhandled_exception",
        exc_type=exc_type,
        exc_message=str(exc),
        exc_traceback=exc_traceback,
        path=request.url.path,
        method=request.method,
        client_host=request.client.host if request.client else None,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "detail": str(exc) if settings.DEBUG else "An error occurred"
            }
        }
    )


# 额外的异常日志记录
def log_exception(exc_type, value, tb):
    """Log uncaught exceptions."""
    logger.error(
        "uncaught_exception",
        exc_type=exc_type.__name__,
        exc_message=str(value),
        exc_traceback="".join(traceback.format_exception(exc_type, value, tb)),
    )
    # 调用原始的异常处理
    sys.__excepthook__(exc_type, value, tb)


# 设置全局异常钩子
sys.excepthook = log_exception


@app.get("/api/system/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.0.3"}


@app.get("/api/system/version")
async def get_version() -> dict:
    """Get version information."""
    return {"version": "0.0.3", "name": "JustFit"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Allow network access
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
