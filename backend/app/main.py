"""FastAPI entry point for the local AquaSense Mini-Build API."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from .auth import authenticate, require_token
from .data import get_device, tank_readings
from .models import DeviceStatus, LoginRequest, LoginResponse, TankReading, TankSummary
from .time_utils import (
    FUTURE_TIMESTAMP_TOLERANCE_SECONDS,
    READING_STALE_AFTER_SECONDS,
    STALE_AFTER_SECONDS,
    is_timestamp_stale,
    parse_and_normalize_timestamp,
    validate_not_future,
)

app = FastAPI(
    title="AquaSense API",
    description="Backend API for AquaSense",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "*",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
bearer_scheme = HTTPBearer(auto_error=False)
LOW_LEVEL_THRESHOLD = 20


def _resolve_frontend_dir() -> Path:
    primary = Path(__file__).resolve().parents[2] / "frontend"
    if primary.exists():
        return primary
    cwd_candidate = Path.cwd() / "frontend"
    if cwd_candidate.exists():
        return cwd_candidate
    return primary


FRONTEND_DIR = _resolve_frontend_dir()


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
        raw_readings = tank_readings()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Mock data contains an invalid tank reading") from exc

    if not raw_readings:
        return []

    readings: list[TankReading] = []
    for item in raw_readings:
        try:
            readings.append(TankReading.model_validate(item))
        except ValueError as exc:
            err_str = str(exc).lower()
            if "in the future" in err_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tank reading timestamp is in the future beyond allowed tolerance",
                ) from exc
            raise HTTPException(status_code=500, detail="Mock data contains an invalid tank reading") from exc
        except (TypeError, Exception) as exc:
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

    # Validate and normalize device timestamp to UTC
    try:
        last_seen_utc = parse_and_normalize_timestamp(device["last_seen"])
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Device last_seen is malformed") from exc

    # Reject future timestamps exceeding the configured tolerance window (5 minutes)
    try:
        validate_not_future(last_seen_utc, tolerance_seconds=FUTURE_TIMESTAMP_TOLERANCE_SECONDS)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device last_seen timestamp is in the future beyond allowed tolerance",
        ) from exc

    raw_level = device.get("level_percent") if "level_percent" in device else device.get("level")
    if raw_level is None:
        raw_level = 55.0
    elif isinstance(raw_level, bool) or not isinstance(raw_level, (int, float)) or not 0 <= raw_level <= 100:
        raise HTTPException(status_code=500, detail="Device record is malformed")

    pump_state = device.get("pump_state")
    if pump_state is None:
        pump_state = "off"
    elif pump_state not in ("on", "off"):
        raise HTTPException(status_code=500, detail="Device record is malformed")

    is_stale = is_timestamp_stale(last_seen_utc, STALE_AFTER_SECONDS)
    return DeviceStatus(
        id=device_id,
        online=True,
        last_seen=last_seen_utc,
        is_stale=is_stale,
        status="stale" if is_stale else "online",
        level_percent=float(raw_level),
        pump_state=pump_state,
    )


@app.get("/api/tank/summary", response_model=TankSummary)
def tank_summary() -> TankSummary:
    """Summarize the JSON readings; active alert uses only the latest reading."""
    readings = _validated_readings()
    if not readings:
        return TankSummary(
            current_level=0.0,
            minimum_level=0.0,
            maximum_level=0.0,
            active_alert=False,
            historical_low_events=[],
            readings=[],
            is_stale=True,
            latest_reading_timestamp=None,
        )

    latest_reading = readings[-1]
    current = latest_reading.level
    is_stale = is_timestamp_stale(latest_reading.timestamp, READING_STALE_AFTER_SECONDS)
    historical_lows = [reading for reading in readings if reading.level < LOW_LEVEL_THRESHOLD]
    return TankSummary(
        current_level=current,
        minimum_level=min(reading.level for reading in readings),
        maximum_level=max(reading.level for reading in readings),
        active_alert=current < LOW_LEVEL_THRESHOLD,
        historical_low_events=historical_lows,
        readings=readings,
        is_stale=is_stale,
        latest_reading_timestamp=latest_reading.timestamp,
    )


# Keep this catch-all mount last so API and documentation routes take precedence.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
