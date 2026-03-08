from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str
    details: dict = {}


class ResponseMeta(BaseModel):
    timestamp: datetime
    duration_ms: int
    version: str = "1.0.0"


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ApiError] = None
    meta: ResponseMeta


def success_response(data: T, duration_ms: int = 0) -> dict:
    """Build a success response envelope."""
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "version": "1.0.0",
        },
    }


def error_response(code: str, message: str, details: dict | None = None, duration_ms: int = 0) -> dict:
    """Build an error response envelope."""
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "version": "1.0.0",
        },
    }
