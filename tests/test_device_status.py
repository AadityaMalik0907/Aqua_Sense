"""Automated API tests for AquaSense device status endpoint."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.time_utils import get_current_utc_time

client = TestClient(app)
VALID_AUTH_HEADER = {"Authorization": "Bearer aquasense-demo-token"}
INVALID_AUTH_HEADER = {"Authorization": "Bearer invalid-token-xyz"}


def test_device_status_valid_token():
    """Scenario 3: Access device status with a valid token (deterministic via dynamic fresh timestamp)."""
    now_utc = get_current_utc_time()
    fresh_record = {
        "id": "tank-001",
        "online": True,
        "last_seen": (now_utc - timedelta(minutes=10)).isoformat(),
        "level_percent": 55.0,
        "pump_state": "off",
    }
    with patch("backend.app.main.get_device", return_value=fresh_record):
        response = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "tank-001"
        assert body["online"] is True
        assert body["status"] == "online"
        assert body["is_stale"] is False
        assert "last_seen" in body
        assert body["level_percent"] == 55.0
        assert body["pump_state"] == "off"


def test_device_status_invalid_token():
    """Scenario 4: Access device status with an invalid token."""
    response = client.get("/device/tank-001/status", headers=INVALID_AUTH_HEADER)
    
    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "Invalid bearer token"


def test_device_status_missing_token():
    """Scenario 5: Access device status without a token."""
    response = client.get("/device/tank-001/status")
    
    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "Bearer token required"


def test_device_status_nonexistent_device():
    """Scenario 6: Request a nonexistent device."""
    response = client.get("/device/nonexistent-device-999/status", headers=VALID_AUTH_HEADER)
    
    assert response.status_code == 404
    body = response.json()
    assert body["detail"] == "Device not found"


def test_device_status_offline_device():
    """Scenario 7: Handle an offline device."""
    response = client.get("/device/device-offline/status", headers=VALID_AUTH_HEADER)
    
    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == {
        "message": "Device is offline",
        "device_id": "device-offline",
    }


def test_device_status_malformed_record():
    """Scenario 8: Handle malformed device record where 'online' is not a boolean."""
    malformed_record = {
        "id": "device-malformed",
        "online": "not-a-boolean",
        "last_seen": "2026-11-04T12:00:00+05:30",
    }
    with patch("backend.app.main.get_device", return_value=malformed_record):
        response = client.get("/device/device-malformed/status", headers=VALID_AUTH_HEADER)
        
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Device record is malformed"


def test_device_status_malformed_timestamp():
    """Scenario 8 (continued): Handle malformed device record where 'last_seen' is not a valid ISO date."""
    malformed_timestamp_record = {
        "id": "device-bad-date",
        "online": True,
        "last_seen": "invalid-non-iso-timestamp",
    }
    with patch("backend.app.main.get_device", return_value=malformed_timestamp_record):
        response = client.get("/device/device-bad-date/status", headers=VALID_AUTH_HEADER)
        
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Device last_seen is malformed"


def test_device_status_missing_last_seen():
    """Verify device record missing the 'last_seen' field returns 500 malformed error."""
    missing_last_seen_record = {
        "id": "device-missing-last-seen",
        "online": True,
        # 'last_seen' key completely absent
    }
    with patch("backend.app.main.get_device", return_value=missing_last_seen_record):
        response = client.get("/device/device-missing-last-seen/status", headers=VALID_AUTH_HEADER)
        
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Device record is malformed"


def test_device_status_stale_timestamp():
    """Scenario 9: Handle stale last_seen timestamps older than 24 hours deterministically."""
    now_utc = get_current_utc_time()
    stale_record = {
        "id": "device-stale",
        "online": True,
        "last_seen": (now_utc - timedelta(hours=25)).isoformat(),
    }
    with patch("backend.app.main.get_device", return_value=stale_record):
        response = client.get("/device/device-stale/status", headers=VALID_AUTH_HEADER)
        
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == "device-stale"
        assert body["online"] is True
        assert body["is_stale"] is True
        assert body["status"] == "stale"
        assert "last_seen" in body


def test_device_status_future_beyond_tolerance_rejected():
    """Reject device last_seen timestamp more than 5 minutes in the future."""
    now_utc = get_current_utc_time()
    future_record = {
        "id": "device-future",
        "online": True,
        "last_seen": (now_utc + timedelta(minutes=10)).isoformat(),
    }
    with patch("backend.app.main.get_device", return_value=future_record):
        response = client.get("/device/device-future/status", headers=VALID_AUTH_HEADER)
        
        assert response.status_code == 400
        body = response.json()
        assert "future" in body["detail"].lower()


def test_device_status_future_within_tolerance_accepted():
    """Accept device last_seen timestamp within the 5-minute future tolerance."""
    now_utc = get_current_utc_time()
    slight_future_record = {
        "id": "device-slight-future",
        "online": True,
        "last_seen": (now_utc + timedelta(minutes=2)).isoformat(),
    }
    with patch("backend.app.main.get_device", return_value=slight_future_record):
        response = client.get("/device/device-slight-future/status", headers=VALID_AUTH_HEADER)
        
        assert response.status_code == 200
        body = response.json()
        assert body["online"] is True
        assert body["is_stale"] is False


def test_device_status_response_schema_contract():
    """Verify device status response strictly adheres to exact contract schema, keys, and data types."""
    now_utc = get_current_utc_time()
    record = {
        "id": "tank-001",
        "online": True,
        "last_seen": (now_utc - timedelta(minutes=5)).isoformat(),
        "level_percent": 72.5,
        "pump_state": "on",
    }
    with patch("backend.app.main.get_device", return_value=record):
        response = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert response.status_code == 200
        body = response.json()
        
        # Verify exact field presence
        expected_keys = {"id", "online", "status", "last_seen", "is_stale", "level_percent", "pump_state"}
        assert set(body.keys()) == expected_keys
        
        # Verify data types and constraints
        assert isinstance(body["id"], str) and body["id"] == "tank-001"
        assert isinstance(body["online"], bool) and body["online"] is True
        assert isinstance(body["status"], str) and body["status"] == "online"
        assert isinstance(body["is_stale"], bool) and body["is_stale"] is False
        assert isinstance(body["last_seen"], str) and body["last_seen"].endswith("Z") or "+00:00" in body["last_seen"]
        assert isinstance(body["level_percent"], (int, float)) and body["level_percent"] == 72.5
        assert isinstance(body["pump_state"], str) and body["pump_state"] in ("on", "off")


def test_device_status_pump_state_validation():
    """Verify pump_state accepts 'on' and 'off', and rejects invalid states."""
    now_utc = get_current_utc_time()
    base_record = {
        "id": "tank-001",
        "online": True,
        "last_seen": (now_utc - timedelta(minutes=5)).isoformat(),
        "level_percent": 50.0,
    }

    # Valid 'on'
    with patch("backend.app.main.get_device", return_value={**base_record, "pump_state": "on"}):
        resp_on = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp_on.status_code == 200
        assert resp_on.json()["pump_state"] == "on"

    # Valid 'off'
    with patch("backend.app.main.get_device", return_value={**base_record, "pump_state": "off"}):
        resp_off = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp_off.status_code == 200
        assert resp_off.json()["pump_state"] == "off"

    # Invalid pump state
    with patch("backend.app.main.get_device", return_value={**base_record, "pump_state": "broken"}):
        resp_invalid = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp_invalid.status_code == 500
        assert resp_invalid.json()["detail"] == "Device record is malformed"


def test_device_status_level_percent_boundary_validation():
    """Verify level_percent validates 0% to 100% boundary on device status."""
    now_utc = get_current_utc_time()
    base_record = {
        "id": "tank-001",
        "online": True,
        "last_seen": (now_utc - timedelta(minutes=5)).isoformat(),
        "pump_state": "off",
    }

    # Boundary 0%
    with patch("backend.app.main.get_device", return_value={**base_record, "level_percent": 0.0}):
        resp_0 = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp_0.status_code == 200
        assert resp_0.json()["level_percent"] == 0.0

    # Boundary 100%
    with patch("backend.app.main.get_device", return_value={**base_record, "level_percent": 100.0}):
        resp_100 = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp_100.status_code == 200
        assert resp_100.json()["level_percent"] == 100.0

    # Below 0% rejected
    with patch("backend.app.main.get_device", return_value={**base_record, "level_percent": -1.0}):
        resp_neg = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp_neg.status_code == 500
        assert resp_neg.json()["detail"] == "Device record is malformed"

    # Above 100% rejected
    with patch("backend.app.main.get_device", return_value={**base_record, "level_percent": 100.5}):
        resp_over = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
        assert resp_over.status_code == 500
        assert resp_over.json()["detail"] == "Device record is malformed"

