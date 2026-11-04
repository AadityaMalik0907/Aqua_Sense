"""Automated API and model boundary tests for AquaSense tank level measurements."""

from datetime import timedelta
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models import TankReading
from backend.app.time_utils import get_current_utc_time

client = TestClient(app)


def test_tank_level_boundary_zero_percent_accepted():
    """Scenario 10a: Boundary check - 0% level reading must be accepted."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    mock_payload = {
        "tank_readings": [
            {"timestamp": safe_ts, "level": 0.0}
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 0.0
        assert body["minimum_level"] == 0.0
        assert body["maximum_level"] == 0.0
        assert body["active_alert"] is True
        assert len(body["readings"]) == 1
        assert body["readings"][0]["level"] == 0.0


def test_tank_level_boundary_hundred_percent_accepted():
    """Scenario 10b: Boundary check - 100% level reading must be accepted."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    mock_payload = {
        "tank_readings": [
            {"timestamp": safe_ts, "level": 100.0}
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 100.0
        assert body["minimum_level"] == 100.0
        assert body["maximum_level"] == 100.0
        assert body["active_alert"] is False
        assert len(body["readings"]) == 1
        assert body["readings"][0]["level"] == 100.0


def test_tank_level_boundary_below_zero_rejected():
    """Scenario 10c: Boundary check - values below 0% must be rejected."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    mock_payload = {
        "tank_readings": [
            {"timestamp": safe_ts, "level": -1.0}
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Tank reading level must be between 0 and 100"


def test_tank_level_boundary_above_hundred_rejected():
    """Scenario 10d: Boundary check - values above 100% must be rejected."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    mock_payload = {
        "tank_readings": [
            {"timestamp": safe_ts, "level": 100.5}
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        
        assert response.status_code == 500
        body = response.json()
        assert body["detail"] == "Tank reading level must be between 0 and 100"


def test_tank_reading_model_boundary_validation():
    """Scenario 10e: Pydantic model validation on TankReading boundary constraints."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    
    valid_lower = TankReading(timestamp=safe_ts, level=0)
    assert valid_lower.level == 0.0

    valid_upper = TankReading(timestamp=safe_ts, level=100)
    assert valid_upper.level == 100.0

    with pytest.raises(ValidationError):
        TankReading(timestamp=safe_ts, level=-0.1)

    with pytest.raises(ValidationError):
        TankReading(timestamp=safe_ts, level=100.1)


def test_tank_level_boundary_19_9_percent_active_alert():
    """Verify that a reading of 19.9% triggers an active low-level alert (<20%)."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    mock_payload = {"tank_readings": [{"timestamp": safe_ts, "level": 19.9}]}
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 19.9
        assert body["active_alert"] is True
        assert len(body["historical_low_events"]) == 1
        assert body["historical_low_events"][0]["level"] == 19.9


def test_tank_level_boundary_20_0_percent_nominal():
    """Verify that a reading of exactly 20.0% is nominal (NOT an active alert)."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    mock_payload = {"tank_readings": [{"timestamp": safe_ts, "level": 20.0}]}
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 20.0
        assert body["active_alert"] is False
        assert len(body["historical_low_events"]) == 0


def test_tank_level_boundary_20_1_percent_nominal():
    """Verify that a reading of 20.1% is nominal (NOT an active alert)."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=10)).isoformat()
    mock_payload = {"tank_readings": [{"timestamp": safe_ts, "level": 20.1}]}
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 20.1
        assert body["active_alert"] is False
        assert len(body["historical_low_events"]) == 0


def test_tank_summary_empty_readings_graceful():
    """Verify that empty reading history returns zeroed summary marked stale."""
    with patch("backend.app.data.load_data", return_value={"tank_readings": []}):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 0.0
        assert body["minimum_level"] == 0.0
        assert body["maximum_level"] == 0.0
        assert body["active_alert"] is False
        assert body["readings"] == []
        assert body["historical_low_events"] == []
        assert body["is_stale"] is True
        assert body["latest_reading_timestamp"] is None


def test_tank_summary_malformed_reading_missing_level():
    """Verify that a reading missing the level attribute raises 500."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=5)).isoformat()
    with patch("backend.app.data.load_data", return_value={"tank_readings": [{"timestamp": safe_ts}]}):
        response = client.get("/api/tank/summary")
        assert response.status_code == 500
        assert "malformed tank reading" in response.json()["detail"].lower()


def test_tank_summary_malformed_reading_non_numeric():
    """Verify that a reading with a non-numeric level raises 500."""
    safe_ts = (get_current_utc_time() - timedelta(minutes=5)).isoformat()
    with patch("backend.app.data.load_data", return_value={"tank_readings": [{"timestamp": safe_ts, "level": "seventy"}]}):
        response = client.get("/api/tank/summary")
        assert response.status_code == 500
        assert "level must be between 0 and 100" in response.json()["detail"].lower()


def test_tank_summary_historical_low_event_distinction():
    """Verify that an earlier low reading (18%) is recorded as a historical event

    while the current nominal reading (55%) produces NO active alert.
    """
    now_utc = get_current_utc_time()
    t_past = (now_utc - timedelta(hours=4)).isoformat()
    t_now = (now_utc - timedelta(minutes=10)).isoformat()
    mock_payload = {
        "tank_readings": [
            {"timestamp": t_past, "level": 18.0},
            {"timestamp": t_now, "level": 55.0},
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 55.0
        assert body["minimum_level"] == 18.0
        assert body["maximum_level"] == 55.0
        assert body["active_alert"] is False  # Current is 55.0, not < 20
        assert len(body["historical_low_events"]) == 1
        assert body["historical_low_events"][0]["level"] == 18.0


def test_tank_summary_active_low_level_alert():
    """Verify that when the latest reading breaches 20%, an active alert is raised."""
    now_utc = get_current_utc_time()
    t_past = (now_utc - timedelta(hours=4)).isoformat()
    t_now = (now_utc - timedelta(minutes=10)).isoformat()
    mock_payload = {
        "tank_readings": [
            {"timestamp": t_past, "level": 55.0},
            {"timestamp": t_now, "level": 18.0},
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_payload):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        body = response.json()
        assert body["current_level"] == 18.0
        assert body["minimum_level"] == 18.0
        assert body["maximum_level"] == 55.0
        assert body["active_alert"] is True  # Latest reading 18.0 is < 20
        assert len(body["historical_low_events"]) == 1

