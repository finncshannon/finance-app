import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

from models.response import success_response, error_response

router = APIRouter(prefix="/api/v1/system", tags=["system"])

_start_time = time.time()


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint polled by Electron on startup."""
    start = time.time()
    uptime = round(time.time() - _start_time, 1)

    db_status = "disconnected"
    try:
        db = request.app.state.db
        if db._conn is not None:
            await db.fetchone("SELECT 1")
            db_status = "connected"
    except Exception:
        pass

    duration_ms = round((time.time() - start) * 1000)
    return success_response(
        data={
            "status": "healthy",
            "uptime": uptime,
            "db_status": db_status,
        },
        duration_ms=duration_ms,
    )


@router.get("/status")
async def system_status(request: Request):
    """System status with database sizes, cache stats."""
    import os
    db = request.app.state.db
    user_size = 0
    cache_size = 0
    try:
        if db.user_db_path.exists():
            user_size = os.path.getsize(db.user_db_path)
        if db.cache_db_path.exists():
            cache_size = os.path.getsize(db.cache_db_path)
    except Exception:
        pass

    return success_response(data={
        "user_db_size_bytes": user_size,
        "cache_db_size_bytes": cache_size,
        "uptime": round(time.time() - _start_time, 1),
    })


@router.post("/clear-cache")
async def clear_cache(request: Request):
    """Clear market_cache.db tables."""
    db = request.app.state.db
    try:
        for table in ["cache.financial_data", "cache.market_data", "cache.filing_cache",
                       "cache.filing_sections", "cache.company_events"]:
            await db.execute(f"DELETE FROM {table}")
        await db.commit()
        return success_response(data={"cleared": True})
    except Exception as e:
        return error_response("DATABASE_ERROR", str(e))


class BackupRequest(BaseModel):
    filename: str | None = None


@router.post("/backup")
async def trigger_backup(request: Request):
    """Trigger manual backup of user_data.db."""
    backup_svc = request.app.state.backup_service
    try:
        result = await backup_svc.create_backup()
        return success_response(data=result)
    except Exception as e:
        return error_response("DATABASE_ERROR", f"Backup failed: {e}")


@router.get("/backups")
async def list_backups(request: Request):
    """List available backup files with dates and sizes."""
    backup_svc = request.app.state.backup_service
    backups = backup_svc.list_backups()
    return success_response(data={"backups": backups})


@router.post("/restore")
async def restore_backup(request: Request, body: BackupRequest):
    """Restore user_data.db from a backup file."""
    if not body.filename:
        return error_response("VALIDATION_ERROR", "filename is required")

    backup_svc = request.app.state.backup_service
    try:
        result = await backup_svc.restore_backup(body.filename)
        return success_response(data=result)
    except FileNotFoundError:
        return error_response("VALIDATION_ERROR", f"Backup file not found: {body.filename}")
    except Exception as e:
        return error_response("DATABASE_ERROR", f"Restore failed: {e}")
