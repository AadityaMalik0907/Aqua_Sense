"""FastAPI entry point for the local AquaSense Mini-Build API."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from .auth import authenticate, require_token
from .data import get_device, tank_readings
from .models import DeviceStatus, LoginRequest, LoginResponse, TankReading, TankSummary

app = FastAPI(
    title="AquaSense API",
    description="Backend API for AquaSense",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
bearer_scheme = HTTPBearer(auto_error=False)
STALE_AFTER_SECONDS = 24 * 60 * 60
LOW_LEVEL_THRESHOLD = 20
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/api")
def api_info() -> dict[str, str]:
    """Provide API information while the site itself is served at /."""
    return {
        "message": "Welcome to AquaSense API",
        "status": "running",
        "docs": "/docs",
    }


def _validated_readings() -> list[TankReading]:
    """Convert validated JSON readings to typed readings, sorted by time."""
    try:
        readings = [TankReading.model_validate(item) for item in tank_readings()]
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="Mock data contains an invalid tank reading") from exc
    return sorted(readings, key=lambda reading: reading.timestamp)


@app.get("/health")
def health() -> dict[str, str]:
    """Lightweight process health check; does not require authentication."""
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    """Validate the documented mock credentials and issue a bearer token."""
    token = authenticate(request.username, request.password)
    return LoginResponse(access_token=token)


@app.get("/device/{device_id}/status", response_model=DeviceStatus)
def device_status(
    device_id: str,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> DeviceStatus:
    """Return a device's connection state; stale devices remain inspectable."""
    require_token(credentials)
    device = get_device(device_id)
    if not isinstance(device.get("online"), bool) or not isinstance(device.get("last_seen"), str):
        raise HTTPException(status_code=500, detail="Device record is malformed")
    if not device["online"]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail={"message": "Device is offline", "device_id": device_id})
    try:
        last_seen = datetime.fromisoformat(device["last_seen"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Device last_seen is malformed") from exc
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - last_seen.astimezone(timezone.utc)).total_seconds()
    is_stale = age_seconds > STALE_AFTER_SECONDS
    return DeviceStatus(id=device_id, online=True, last_seen=last_seen,
                        is_stale=is_stale, status="stale" if is_stale else "online")


@app.get("/api/tank/summary", response_model=TankSummary)
def tank_summary() -> TankSummary:
    """Summarize the JSON readings; active alert uses only the latest reading."""
    readings = _validated_readings()
    current = readings[-1].level
    historical_lows = [reading for reading in readings if reading.level < LOW_LEVEL_THRESHOLD]
    return TankSummary(
        current_level=current,
        minimum_level=min(reading.level for reading in readings),
        maximum_level=max(reading.level for reading in readings),
        active_alert=current < LOW_LEVEL_THRESHOLD,
        historical_low_events=historical_lows,
        readings=readings,
    )


# Keep this catch-all mount last so API and documentation routes take precedence.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
