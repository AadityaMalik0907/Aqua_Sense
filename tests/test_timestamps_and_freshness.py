"""Automated tests for timestamp normalization, timezone handling, and data freshness."""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import TankReading, TankSummary
from backend.app.time_utils import (
    get_current_utc_time,
    parse_and_normalize_timestamp,
    validate_not_future,
    is_timestamp_stale,
    FUTURE_TIMESTAMP_TOLERANCE_SECONDS,
)

client = TestClient(app)
VALID_AUTH_HEADER = {"Authorization": "Bearer aquasense-demo-token"}


# ---------------------------------------------------------------------------
# 1. Valid Timezone-Aware Timestamps
# ---------------------------------------------------------------------------
def test_valid_timezone_aware_timestamps():
    """Verify timezone-aware timestamps with explicit offsets are normalized to UTC."""
    # UTC ISO string
    ts_utc = "2026-11-04T10:00:00Z"
    dt1 = parse_and_normalize_timestamp(ts_utc)
    assert dt1.tzinfo == timezone.utc
    assert dt1.hour == 10

    # India Standard Time (+05:30)
    ts_ist = "2026-11-04T15:30:00+05:30"
    dt2 = parse_and_normalize_timestamp(ts_ist)
    assert dt2.tzinfo == timezone.utc
    assert dt2.hour == 10  # 15:30 - 5:30 = 10:00 UTC
    assert dt1 == dt2

    # US Eastern Daylight Time (-04:00)
    ts_edt = "2026-11-04T06:00:00-04:00"
    dt3 = parse_and_normalize_timestamp(ts_edt)
    assert dt3.tzinfo == timezone.utc
    assert dt3.hour == 10  # 06:00 + 4:00 = 10:00 UTC
    assert dt1 == dt3


# ---------------------------------------------------------------------------
# 2. Mixed Timezone Offsets
# ---------------------------------------------------------------------------
def test_mixed_timezone_offsets_chronological_ordering():
    """Readings from mixed timezones must be normalized and chronologically sorted by UTC time."""
    now_utc = get_current_utc_time()
    
    # Reading A: 12:00 UTC
    time_a = now_utc - timedelta(hours=3)
    # Reading B: 11:30 UTC expressed in IST (+05:30 -> 17:00 IST)
    time_b = time_a - timedelta(minutes=30)
    # Reading C: 13:00 UTC expressed in EDT (-04:00 -> 09:00 EDT)
    time_c = time_a + timedelta(hours=1)

    mock_readings = [
        {"timestamp": time_c.isoformat(), "level": 80.0},
        {"timestamp": time_a.isoformat(), "level": 50.0},
        {"timestamp": time_b.isoformat(), "level": 20.0},
    ]

    with patch("backend.app.data.load_data", return_value={"tank_readings": mock_readings}):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        data = response.json()
        readings = data["readings"]
        assert len(readings) == 3
        # Chronological order should be B (earliest), A (middle), C (latest)
        assert readings[0]["level"] == 20.0
        assert readings[1]["level"] == 50.0
        assert readings[2]["level"] == 80.0
        assert data["current_level"] == 80.0


# ---------------------------------------------------------------------------
# 3. Naive Timestamps Rejection
# ---------------------------------------------------------------------------
def test_naive_timestamp_rejected_without_silent_utc_assumption():
    """Timezone-naive timestamps must not be silently treated as UTC and must be rejected."""
    naive_ts = "2026-11-04T12:00:00"  # No 'Z' and no offset
    
    with pytest.raises(ValueError, match="Timezone offset is required"):
        parse_and_normalize_timestamp(naive_ts)

    # In Pydantic model validation
    with pytest.raises(ValidationError):
        TankReading(timestamp=naive_ts, level=50.0)

    # In summary API
    with patch("backend.app.data.load_data", return_value={"tank_readings": [{"timestamp": naive_ts, "level": 50.0}]}):
        response = client.get("/api/tank/summary")
        assert response.status_code == 500
        assert "invalid tank reading" in response.json()["detail"].lower()


def test_invalid_unparseable_timestamp_rejected():
    """Completely unparseable and malformed timestamp strings must be rejected."""
    invalid_strings = [
        "not-a-timestamp",
        "2026-99-99T99:99:99Z",
        "2026-11-04",  # Missing time component
        "",
    ]
    for bad_ts in invalid_strings:
        with pytest.raises(ValueError):
            parse_and_normalize_timestamp(bad_ts)

        with pytest.raises(ValidationError):
            TankReading(timestamp=bad_ts, level=50.0)

    # Passing non-str, non-datetime types
    with pytest.raises(ValueError, match="Expected str or datetime"):
        parse_and_normalize_timestamp(123456)

    # API returns 500 when mock data contains an unparseable timestamp
    with patch("backend.app.data.load_data", return_value={"tank_readings": [{"timestamp": "corrupt-ts", "level": 50.0}]}):
        response = client.get("/api/tank/summary")
        assert response.status_code == 500
        assert "invalid tank reading" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 4. Future Timestamps Within 5-Minute Tolerance
# ---------------------------------------------------------------------------
def test_future_timestamp_within_tolerance_accepted():
    """Timestamps slightly ahead of UTC time (<= 5 minutes) must be accepted."""
    now_utc = get_current_utc_time()
    tolerated_future = now_utc + timedelta(minutes=3)

    # Utility level
    validated = validate_not_future(tolerated_future)
    assert validated == tolerated_future

    # Model level
    reading = TankReading(timestamp=tolerated_future, level=60.0)
    assert reading.level == 60.0

    # API level
    mock_data = {"tank_readings": [{"timestamp": tolerated_future.isoformat(), "level": 60.0}]}
    with patch("backend.app.data.load_data", return_value=mock_data):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        assert response.json()["current_level"] == 60.0


# ---------------------------------------------------------------------------
# 5. Future Timestamps Beyond Tolerance
# ---------------------------------------------------------------------------
def test_future_timestamp_beyond_tolerance_rejected():
    """Timestamps more than 5 minutes ahead of current UTC time must be rejected."""
    now_utc = get_current_utc_time()
    excessive_future = now_utc + timedelta(minutes=6)

    # Utility level
    with pytest.raises(ValueError, match="in the future"):
        validate_not_future(excessive_future)

    # Model level
    with pytest.raises(ValidationError):
        TankReading(timestamp=excessive_future, level=60.0)

    # API level
    mock_data = {"tank_readings": [{"timestamp": excessive_future.isoformat(), "level": 60.0}]}
    with patch("backend.app.data.load_data", return_value=mock_data):
        response = client.get("/api/tank/summary")
        assert response.status_code == 400
        assert "future" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Stale Tank Readings (> 24 Hours)
# ---------------------------------------------------------------------------
def test_stale_tank_readings_flagged_not_live():
    """Readings older than 24 hours must be marked as stale (is_stale=True) while preserving history."""
    now_utc = get_current_utc_time()
    stale_timestamp = now_utc - timedelta(hours=26)

    mock_data = {
        "tank_readings": [
            {"timestamp": (stale_timestamp - timedelta(hours=2)).isoformat(), "level": 15.0},
            {"timestamp": stale_timestamp.isoformat(), "level": 45.0},
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_data):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        data = response.json()
        
        # Freshness flag
        assert data["is_stale"] is True
        assert data["latest_reading_timestamp"] is not None
        # Data preservation
        assert data["current_level"] == 45.0
        assert len(data["readings"]) == 2
        assert len(data["historical_low_events"]) == 1


# ---------------------------------------------------------------------------
# 7. Fresh Tank Readings (<= 24 Hours)
# ---------------------------------------------------------------------------
def test_fresh_tank_readings_flagged_live():
    """Readings within the 24-hour freshness threshold must report is_stale=False."""
    now_utc = get_current_utc_time()
    fresh_timestamp = now_utc - timedelta(minutes=15)

    mock_data = {
        "tank_readings": [
            {"timestamp": (fresh_timestamp - timedelta(hours=1)).isoformat(), "level": 60.0},
            {"timestamp": fresh_timestamp.isoformat(), "level": 70.0},
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_data):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["is_stale"] is False
        assert data["current_level"] == 70.0


# ---------------------------------------------------------------------------
# 8. Empty Reading History
# ---------------------------------------------------------------------------
def test_empty_reading_history_handled_gracefully():
    """Empty reading history must return an empty summary marked as stale without 500 error."""
    mock_data = {"tank_readings": []}
    with patch("backend.app.data.load_data", return_value=mock_data):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["current_level"] == 0.0
        assert data["minimum_level"] == 0.0
        assert data["maximum_level"] == 0.0
        assert data["readings"] == []
        assert data["is_stale"] is True
        assert data["latest_reading_timestamp"] is None


# ---------------------------------------------------------------------------
# 9. Correct Chronological Ordering
# ---------------------------------------------------------------------------
def test_chronological_ordering_guarantee():
    """Unsorted input readings must be strictly returned in ascending UTC chronological order."""
    now_utc = get_current_utc_time()
    t1 = now_utc - timedelta(hours=5)
    t2 = now_utc - timedelta(hours=3)
    t3 = now_utc - timedelta(hours=1)

    # Provide readings in reverse order
    mock_data = {
        "tank_readings": [
            {"timestamp": t3.isoformat(), "level": 90.0},
            {"timestamp": t1.isoformat(), "level": 30.0},
            {"timestamp": t2.isoformat(), "level": 60.0},
        ]
    }
    with patch("backend.app.data.load_data", return_value=mock_data):
        response = client.get("/api/tank/summary")
        assert response.status_code == 200
        readings = response.json()["readings"]
        assert readings[0]["level"] == 30.0
        assert readings[1]["level"] == 60.0
        assert readings[2]["level"] == 90.0


# ---------------------------------------------------------------------------
# 10. Device Status Future and Stale Timestamps
# ---------------------------------------------------------------------------
def test_device_status_future_and_stale_combinations():
    """Test device status endpoint with future timestamp rejection and stale handling."""
    now_utc = get_current_utc_time()

    # Case A: Future device timestamp (>5 minutes ahead)
    future_device = {
        "id": "device-test-future",
        "online": True,
        "last_seen": (now_utc + timedelta(minutes=15)).isoformat(),
    }
    with patch("backend.app.main.get_device", return_value=future_device):
        resp = client.get("/device/device-test-future/status", headers=VALID_AUTH_HEADER)
        assert resp.status_code == 400
        assert "future" in resp.json()["detail"].lower()

    # Case B: Stale device timestamp (>24 hours ago)
    stale_device = {
        "id": "device-test-stale",
        "online": True,
        "last_seen": (now_utc - timedelta(hours=30)).isoformat(),
    }
    with patch("backend.app.main.get_device", return_value=stale_device):
        resp = client.get("/device/device-test-stale/status", headers=VALID_AUTH_HEADER)
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_stale"] is True
        assert body["status"] == "stale"


# ---------------------------------------------------------------------------
# 11. Reference Time Clock Freezing & Naive Rejection
# ---------------------------------------------------------------------------
def test_reference_time_naive_rejected(monkeypatch):
    """Setting a timezone-naive AQUASENSE_REFERENCE_TIME must be rejected without bypass."""
    monkeypatch.setenv("AQUASENSE_REFERENCE_TIME", "2026-11-04T12:00:00")
    with pytest.raises(ValueError, match="Timezone offset is required"):
        get_current_utc_time()


def test_reference_time_aware_freezes_clock(monkeypatch):
    """Setting a timezone-aware AQUASENSE_REFERENCE_TIME successfully freezes time."""
    ref_str = "2026-11-02T20:05:00+05:30"
    monkeypatch.setenv("AQUASENSE_REFERENCE_TIME", ref_str)
    frozen = get_current_utc_time()
    assert frozen.tzinfo == timezone.utc
    # 20:05 IST -> 14:35 UTC
    assert frozen.hour == 14
    assert frozen.minute == 35


# ---------------------------------------------------------------------------
# 12. Actual JSON Mock Data File Integration Tests (Unmocked)
# ---------------------------------------------------------------------------
def test_actual_mock_data_file_tank_summary(monkeypatch):
    """Verify GET /api/tank/summary against the actual repository data/mock_data.json file."""
    # Freeze reference time to 5 minutes after the assignment's final reading (2026-11-02T20:05:00+05:30)
    monkeypatch.setenv("AQUASENSE_REFERENCE_TIME", "2026-11-02T20:05:00+05:30")
    
    # Make request directly without any monkeypatching/mocking of load_data
    response = client.get("/api/tank/summary")
    assert response.status_code == 200
    body = response.json()

    # Verify assignment telemetry specs
    assert body["current_level"] == 55.0
    assert body["minimum_level"] == 18.0
    assert body["maximum_level"] == 78.0
    assert body["active_alert"] is False  # 55.0 is not < 20
    assert len(body["readings"]) == 8
    assert len(body["historical_low_events"]) == 1
    assert body["historical_low_events"][0]["level"] == 18.0
    assert body["is_stale"] is False


def test_actual_mock_data_file_device_status(monkeypatch):
    """Verify GET /device/{id}/status endpoints against actual data/mock_data.json devices."""
    monkeypatch.setenv("AQUASENSE_REFERENCE_TIME", "2026-11-02T20:05:00+05:30")

    # 1. tank-001 (online and fresh at reference time)
    resp1 = client.get("/device/tank-001/status", headers=VALID_AUTH_HEADER)
    assert resp1.status_code == 200
    b1 = resp1.json()
    assert b1["id"] == "tank-001"
    assert b1["online"] is True
    assert b1["is_stale"] is False
    assert b1["status"] == "online"
    assert b1["level_percent"] == 55.0
    assert b1["pump_state"] == "off"

    # 2. device-offline (offline -> 503)
    resp2 = client.get("/device/device-offline/status", headers=VALID_AUTH_HEADER)
    assert resp2.status_code == 503
    assert resp2.json()["detail"] == {"message": "Device is offline", "device_id": "device-offline"}

    # 3. device-stale (seen in October -> 200 with stale status)
    resp3 = client.get("/device/device-stale/status", headers=VALID_AUTH_HEADER)
    assert resp3.status_code == 200
    b3 = resp3.json()
    assert b3["id"] == "device-stale"
    assert b3["online"] is True
    assert b3["is_stale"] is True
    assert b3["status"] == "stale"


def test_actual_mock_data_file_tank_summary_wall_clock(monkeypatch):
    """Verify GET /api/tank/summary against actual data/mock_data.json with no reference time (wall clock)."""
    monkeypatch.delenv("AQUASENSE_REFERENCE_TIME", raising=False)
    response = client.get("/api/tank/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["current_level"] == 55.0
    assert len(body["readings"]) == 8
    # Nov 2 readings are in the past (>24h ago relative to Nov 4 wall-clock), correctly marked stale
    assert body["is_stale"] is True


def test_tank_reading_supports_level_percent_alias():
    """Verify TankReading model accepts both 'level' and 'level_percent' fields."""
    safe_ts = "2026-11-02T12:00:00+05:30"
    r1 = TankReading.model_validate({"timestamp": safe_ts, "level": 42.5})
    assert r1.level == 42.5

    r2 = TankReading.model_validate({"timestamp": safe_ts, "level_percent": 64.0})
    assert r2.level == 64.0


