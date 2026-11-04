"""Deterministic Mocked API Tests for AquaSense (Category 5).

Covers:
- Fully deterministic mocked responses without depending on IoT hardware or external networks.
- Verification of malformed, stale, offline, clock-drift, and authentication failure scenarios.
- Strict assertions of HTTP status codes, response bodies, and Pydantic schema contracts.
- HTTPX client async integration test with ASGITransport.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
import httpx
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.time_utils import get_current_utc_time
from backend.app.models import DeviceStatus, TankSummary

client = TestClient(app)
VALID_AUTH_HEADER = {"Authorization": "Bearer aquasense-demo-token"}


# ==============================================================================
# SCENARIO 1: DETERMINISTIC MOCKED NOMINAL TELEMETRY
# ==============================================================================

def test_mocked_tank_summary_nominal_stream():
    """Verify nominal multi-reading telemetry stream via mocked data loader."""
    now_utc = get_current_utc_time()
    mock_readings = [
        {"timestamp": (now_utc - timedelta(minutes=45)).isoformat(), "level": 70.0},
        {"timestamp": (now_utc - timedelta(minutes=30)).isoformat(), "level": 65.0},
        {"timestamp": (now_utc - timedelta(minutes=15)).isoformat(), "level": 60.0},
    ]

    with patch("backend.app.data.load_data", return_value={"tank_readings": mock_readings}) as mock_load:
        response = client.get("/api/tank/summary")
        mock_load.assert_called_once()
        
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 60.0
        assert body["minimum_level"] == 60.0
        assert body["maximum_level"] == 70.0
        assert body["active_alert"] is False
        assert body["is_stale"] is False
        assert len(body["readings"]) == 3
        assert len(body["historical_low_events"]) == 0
        assert body["latest_reading_timestamp"] is not None


# ==============================================================================
# SCENARIO 2: DETERMINISTIC MOCKED STALE TELEMETRY (> 24 HOURS)
# ==============================================================================

def test_mocked_tank_summary_stale_telemetry():
    """Verify that telemetry older than 24 hours is marked is_stale=True while preserving stats."""
    now_utc = get_current_utc_time()
    stale_base = now_utc - timedelta(hours=48)
    mock_readings = [
        {"timestamp": (stale_base - timedelta(hours=4)).isoformat(), "level": 15.0},
        {"timestamp": stale_base.isoformat(), "level": 40.0},
    ]

    with patch("backend.app.data.load_data", return_value={"tank_readings": mock_readings}):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        body = response.json()
        
        assert body["is_stale"] is True
        assert body["current_level"] == 40.0
        assert body["minimum_level"] == 15.0
        assert body["maximum_level"] == 40.0
        assert body["active_alert"] is False  # 40% is >= 20%
        assert len(body["historical_low_events"]) == 1
        assert body["historical_low_events"][0]["level"] == 15.0


# ==============================================================================
# SCENARIO 3: DETERMINISTIC MOCKED CORRUPTED DATA SOURCE
# ==============================================================================

def test_mocked_tank_summary_malformed_data_source():
    """Verify that corrupted data structures raise HTTP 500 without crashing."""
    corrupted_data = {"tank_readings": "not-a-list-structure"}
    with patch("backend.app.data.load_data", return_value=corrupted_data):
        response = client.get("/api/tank/summary")
        assert response.status_code == 500
        assert "no tank readings" in response.json()["detail"].lower()


def test_mocked_tank_summary_reading_not_dict():
    """Verify that non-dict items inside tank_readings raise HTTP 500."""
    corrupted_items = {"tank_readings": [12345, "invalid"]}
    with patch("backend.app.data.load_data", return_value=corrupted_items):
        response = client.get("/api/tank/summary")
        assert response.status_code == 500
        assert "malformed tank reading" in response.json()["detail"].lower()


# ==============================================================================
# SCENARIO 4: DETERMINISTIC MOCKED OFFLINE HARDWARE
# ==============================================================================

def test_mocked_device_status_offline_hardware():
    """Verify that an offline IoT device raises HTTP 503 Service Unavailable."""
    now_utc = get_current_utc_time()
    offline_device = {
        "id": "tank-001",
        "online": False,
        "last_seen": (now_utc - timedelta(minutes=2)).isoformat(),
        "level_percent": 0.0,
        "pump_state": "off",
    }
    with patch("backend.app.main.get_device", return_value=offline_device):
        response = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert response.status_code == 503
        body = response.json()
        assert body["detail"] == {"message": "Device is offline", "device_id": "tank-001"}


# ==============================================================================
# SCENARIO 5: DETERMINISTIC MOCKED STALE HARDWARE
# ==============================================================================

def test_mocked_device_status_stale_hardware():
    """Verify device hardware last seen >24h ago reports status='stale' with HTTP 200."""
    now_utc = get_current_utc_time()
    stale_device = {
        "id": "tank-001",
        "online": True,
        "last_seen": (now_utc - timedelta(hours=36)).isoformat(),
        "level_percent": 55.0,
        "pump_state": "off",
    }
    with patch("backend.app.main.get_device", return_value=stale_device):
        response = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert response.status_code == 200
        body = response.json()
        assert body["online"] is True
        assert body["is_stale"] is True
        assert body["status"] == "stale"
        assert body["level_percent"] == 55.0
        assert body["pump_state"] == "off"


# ==============================================================================
# SCENARIO 6: DETERMINISTIC MOCKED AUTHENTICATION FAILURE
# ==============================================================================

def test_mocked_device_status_auth_failure_rejection():
    """Verify that missing and invalid credentials are rejected with 401."""
    # Missing token
    resp_no_token = client.get("/device/tank-001/status")
    assert resp_no_token.status_code == 401
    assert resp_no_token.json()["detail"] == "Bearer token required"

    # Corrupted token
    resp_bad_token = client.get("/device/tank-001/status", headers={"Authorization": "Bearer bad-token-val"})
    assert resp_bad_token.status_code == 401
    assert resp_bad_token.json()["detail"] == "Invalid bearer token"


# ==============================================================================
# SCENARIO 7: DETERMINISTIC MOCKED HARDWARE FUTURE CLOCK DRIFT
# ==============================================================================

def test_mocked_device_status_future_clock_drift():
    """Verify device last_seen with excessive future drift (>5 minutes) returns HTTP 400."""
    now_utc = get_current_utc_time()
    clock_drift_device = {
        "id": "tank-001",
        "online": True,
        "last_seen": (now_utc + timedelta(minutes=15)).isoformat(),
        "level_percent": 55.0,
        "pump_state": "off",
    }
    with patch("backend.app.main.get_device", return_value=clock_drift_device):
        response = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert response.status_code == 400
        assert "future" in response.json()["detail"].lower()


# ==============================================================================
# SCENARIO 8: DETERMINISTIC MOCKED DEVICE RECORD MISSING REQUIRED FIELDS
# ==============================================================================

def test_mocked_device_status_missing_fields_rejection():
    """Verify device record missing online or last_seen returns HTTP 500."""
    # Missing online
    with patch("backend.app.main.get_device", return_value={"id": "tank-001", "last_seen": "2026-11-04T10:00:00Z"}):
        resp = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Device record is malformed"

    # Missing last_seen
    with patch("backend.app.main.get_device", return_value={"id": "tank-001", "online": True}):
        resp = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp.status_code == 500
        assert resp.json()["detail"] == "Device record is malformed"


# ==============================================================================
# SCENARIO 9: ASYNC HTTPX CLIENT INTEGRATION TEST
# ==============================================================================

@pytest.mark.anyio
async def test_mocked_async_httpx_client_flow():
    """Verify end-to-end async HTTP client interaction using HTTPX and ASGITransport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Health check
        health_resp = await ac.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json() == {"status": "ok"}

        # 2. Authenticate
        login_resp = await ac.post("/login", json={"username": "demo", "password": "aqua123"})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        # 3. Tank summary
        summary_resp = await ac.get("/api/tank/summary")
        assert summary_resp.status_code == 200
        assert "current_level" in summary_resp.json()

        # 4. Authenticated device status
        dev_resp = await ac.get("/device/tank-001/status", headers={"Authorization": f"Bearer {token}"})
        assert dev_resp.status_code == 200
        assert dev_resp.json()["id"] == "tank-001"


# ==============================================================================
# SCENARIO 10: ENDPOINT & DATA LAYER ROBUSTNESS
# ==============================================================================

def test_api_root_endpoint_info():
    """Verify GET /api returns service status and documentation link."""
    response = client.get("/api")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "running"
    assert body["docs"] == "/docs"


def test_mocked_load_data_file_read_error():
    """Verify load_data() handles file I/O or decode errors as HTTP 500."""
    from backend.app.data import load_data
    from fastapi import HTTPException
    with patch("pathlib.Path.open", side_effect=OSError("Disk read error")):
        with pytest.raises(HTTPException) as exc:
            load_data()
        assert exc.value.status_code == 500
        assert "unavailable or malformed" in exc.value.detail


def test_mocked_load_data_non_dict_json():
    """Verify load_data() raises HTTP 500 when JSON payload is not a dict."""
    from backend.app.data import load_data
    from fastapi import HTTPException
    with patch("json.load", return_value=["a", "list"]):
        with pytest.raises(HTTPException) as exc:
            load_data()
        assert exc.value.status_code == 500
        assert "must be a JSON object" in exc.value.detail


def test_mocked_get_device_missing_devices_list():
    """Verify get_device() raises HTTP 500 when 'devices' in payload is not a list."""
    from backend.app.data import get_device
    from fastapi import HTTPException
    with patch("backend.app.data.load_data", return_value={"devices": "not-a-list"}):
        with pytest.raises(HTTPException) as exc:
            get_device("tank-001")
        assert exc.value.status_code == 500
        assert "no valid devices list" in exc.value.detail


def test_validated_readings_unexpected_error_handling():
    """Verify unexpected non-HTTP exceptions in data layer are caught and returned as 500."""
    with patch("backend.app.main.tank_readings", side_effect=RuntimeError("Data layer failure")):
        response = client.get("/api/tank/summary")
        assert response.status_code == 500
        assert "invalid tank reading" in response.json()["detail"].lower()


def test_validated_readings_type_error_handling():
    """Verify TypeError during model validation is mapped to HTTP 500."""
    with patch("backend.app.models.TankReading.model_validate", side_effect=TypeError("Unexpected type conversion error")):
        with patch("backend.app.data.load_data", return_value={"tank_readings": [{"timestamp": "2026-11-04T12:00:00Z", "level": 50}]}):
            response = client.get("/api/tank/summary")
            assert response.status_code == 500
            assert "invalid tank reading" in response.json()["detail"].lower()


def test_resolve_paths_fallback_branches():
    """Verify data and frontend directory resolver fallback branches."""
    from backend.app.data import _resolve_data_file
    from backend.app.main import _resolve_frontend_dir
    from pathlib import Path

    # 1. Fallback when primary doesn't exist but cwd exists
    with patch.object(Path, "exists", side_effect=[False, True]):
        resolved_data = _resolve_data_file()
        assert "mock_data.json" in str(resolved_data)

    with patch.object(Path, "exists", side_effect=[False, True]):
        resolved_front = _resolve_frontend_dir()
        assert "frontend" in str(resolved_front)

    # 2. Fallback when neither exists
    with patch.object(Path, "exists", return_value=False):
        resolved_data_default = _resolve_data_file()
        assert "mock_data.json" in str(resolved_data_default)

    with patch.object(Path, "exists", return_value=False):
        resolved_front_default = _resolve_frontend_dir()
        assert "frontend" in str(resolved_front_default)
