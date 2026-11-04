"""Automated API tests for AquaSense device status endpoint."""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
VALID_AUTH_HEADER = {"Authorization": "Bearer aquasense-demo-token"}
INVALID_AUTH_HEADER = {"Authorization": "Bearer invalid-token-xyz"}


def test_device_status_valid_token():
    """Scenario 3: Access device status with a valid token."""
    response = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
    
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "tank-001"
    assert body["online"] is True
    assert body["status"] == "online"
    assert body["is_stale"] is False
    assert "last_seen" in body


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


def test_device_status_stale_timestamp():
    """Scenario 9: Handle stale last_seen timestamps older than 24 hours."""
    response = client.get("/device/device-stale/status", headers=VALID_AUTH_HEADER)
    
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "device-stale"
    assert body["online"] is True
    assert body["is_stale"] is True
    assert body["status"] == "stale"
    assert "last_seen" in body
