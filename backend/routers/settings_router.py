"""Settings router — GET/PUT endpoints for key-value settings.

Uses SettingsService for business logic, SettingsRepo for persistence.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from models.response import success_response, error_response

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


@router.get("/")
async def get_all_settings(request: Request):
    """Get all settings as a key-value dict."""
    svc = request.app.state.settings_service
    settings = await svc.get_all()
    return success_response(data={"settings": settings})


@router.get("/system-info")
async def get_system_info(request: Request):
    svc = request.app.state.system_info_service
    info = await svc.get_system_info()
    return success_response(data=info)


@router.get("/database-stats")
async def get_database_stats(request: Request):
    svc = request.app.state.system_info_service
    stats = await svc.get_database_stats()
    return success_response(data=stats)


@router.get("/cache-size")
async def get_cache_size(request: Request):
    svc = request.app.state.system_info_service
    size = await svc.get_cache_size()
    return success_response(data=size)


@router.post("/clear-cache")
async def clear_cache(request: Request):
    svc = request.app.state.system_info_service
    result = await svc.clear_cache()
    return success_response(data=result)


@router.get("/{key}")
async def get_setting(key: str, request: Request):
    """Get a single setting by key."""
    svc = request.app.state.settings_service
    value = await svc.get(key)
    if value is None:
        return error_response(
            code="NOT_FOUND",
            message=f"Setting '{key}' not found.",
        )
    return success_response(data={"key": key, "value": value})


@router.put("/")
async def update_settings_bulk(request: Request):
    """Update multiple settings at once. Creates any that don't exist."""
    svc = request.app.state.settings_service
    body = await request.json()
    await svc.set_many(body)
    return success_response(data={"updated": list(body.keys())})


@router.put("/{key}")
async def update_setting(key: str, body: SettingUpdate, request: Request):
    """Update a single setting. Creates if doesn't exist."""
    svc = request.app.state.settings_service
    await svc.set(key, body.value)
    return success_response(data={"key": key, "value": body.value})
