"""Read-only access to the JSON mock data."""

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException


def _resolve_data_file() -> Path:
    primary = Path(__file__).resolve().parents[2] / "data" / "mock_data.json"
    if primary.exists():
        return primary
    cwd_candidate = Path.cwd() / "data" / "mock_data.json"
    if cwd_candidate.exists():
        return cwd_candidate
    return primary


DATA_FILE = _resolve_data_file()


def load_data() -> dict[str, Any]:
    """Load mock data and report malformed/missing data as a server error."""
    try:
        with DATA_FILE.open(encoding="utf-8") as data_file:
            payload = json.load(data_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Mock data is unavailable or malformed") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=500, detail="Mock data must be a JSON object")
    return payload


def get_device(device_id: str) -> dict[str, Any]:
    """Find a device by ID; malformed records are treated as server errors."""
    devices = load_data().get("devices")
    if not isinstance(devices, list):
        raise HTTPException(status_code=500, detail="Mock data has no valid devices list")
    for device in devices:
        if isinstance(device, dict) and device.get("id") == device_id:
            return device
    raise HTTPException(status_code=404, detail="Device not found")


def tank_readings() -> list[dict[str, Any]]:
    """Return readings after checking the JSON structure and level bounds."""
    readings = load_data().get("tank_readings")
    if not isinstance(readings, list):
        raise HTTPException(status_code=500, detail="Mock data has no tank readings")
    for reading in readings:
        if not isinstance(reading, dict) or "timestamp" not in reading:
            raise HTTPException(status_code=500, detail="Malformed tank reading")
        if "level" not in reading and "level_percent" not in reading:
            raise HTTPException(status_code=500, detail="Malformed tank reading")
        level = reading.get("level") if "level" in reading else reading.get("level_percent")
        if isinstance(level, bool) or not isinstance(level, (int, float)) or not 0 <= level <= 100:
            raise HTTPException(status_code=500, detail="Tank reading level must be between 0 and 100")
    return readings
