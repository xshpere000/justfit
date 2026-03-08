"""Application Error Handling."""

from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found error."""

    def __init__(self, message: str = "Resource not found", details: Any = None) -> None:
        super().__init__("NOT_FOUND", message, status.HTTP_404_NOT_FOUND, details)


class ValidationError(AppError):
    """Validation error."""

    def __init__(self, message: str = "Validation failed", details: Any = None) -> None:
        super().__init__("VALIDATION_ERROR", message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class ConnectionError(AppError):
    """Connection error."""

    def __init__(self, message: str = "Connection failed", details: Any = None) -> None:
        super().__init__("CONNECTION_ERROR", message, status.HTTP_502_BAD_GATEWAY, details)


class InternalError(AppError):
    """Internal server error."""

    def __init__(self, message: str = "Internal server error", details: Any = None) -> None:
        super().__init__("INTERNAL_ERROR", message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


def error_response(error: AppError) -> JSONResponse:
    """Create error response."""
    content = {
        "success": False,
        "error": {
            "code": error.code,
            "message": error.message,
        },
    }
    if error.details is not None:
        content["error"]["details"] = error.details
    return JSONResponse(status_code=error.status_code, content=content)
