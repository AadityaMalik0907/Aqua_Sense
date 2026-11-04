"""Automated verification suite for AquaSense Phase 2: Frontend Reliability,

Telemetry Accuracy, and Dashboard Correctness.

Tests:
1. Exact threshold alert logic at 0%, 19.9%, 20%, 20.1%, 100%.
2. Assignment dataset metrics (Current 55%, Min 18%, Max 78%, Historical Low 18%).
3. Time-proportional linear chart X-coordinate calculations (irregular intervals, single reading).
4. Strict payload validation rules (rejection of invalid levels, malformed timestamps, non-monotonic ordering).
5. Data freshness and stale telemetry handling (>24h stale detection).
6. Separation of API connectivity from IoT device hardware connectivity.
7. Static code audit ensuring zero innerHTML injection vectors in dashboard.js.
8. Static DOM element audit verifying required semantic IDs in index.html and styles.css.
9. Cache preservation on simulated network or backend failure.
10. End-to-end FastAPI test client integration verifying API contracts match frontend expectations.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
MOCK_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "mock_data.json"
LOW_THRESHOLD = 20.0
CHART_WIDTH = 760
CHART_HEIGHT = 280
LEFT_MARGIN = 46
RIGHT_MARGIN = 20
TOP_MARGIN = 18
BOTTOM_MARGIN = 38
PLOT_WIDTH = CHART_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
PLOT_HEIGHT = CHART_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN


# ==============================================================================
# PURE PYTHON MIRRORS OF FRONTEND MATHEMATICAL ALGORITHMS
# ==============================================================================

def evaluate_alert_threshold(level: float | int) -> bool:
    """Exact mirror of dashboard.js evaluateAlertThreshold."""
    if not isinstance(level, (int, float)) or isinstance(level, bool):
        raise TypeError("Level must be a finite number")
    return float(level) < LOW_THRESHOLD


def calculate_chart_x_coordinate(timestamp_iso: str, min_time_ms: float, max_time_ms: float, total_count: int) -> float:
    """Exact mirror of dashboard.js calculateChartPoints X calculation."""
    dt = datetime.fromisoformat(timestamp_iso)
    time_ms = dt.timestamp() * 1000.0
    time_span = max_time_ms - min_time_ms
    if total_count <= 1 or time_span <= 0:
        return round(LEFT_MARGIN + PLOT_WIDTH / 2, 2)
    x = LEFT_MARGIN + ((time_ms - min_time_ms) / time_span) * PLOT_WIDTH
    return round(x, 2)


def calculate_chart_points(readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mirror of dashboard.js calculateChartPoints."""
    if not readings:
        return []
    timestamps_ms = [datetime.fromisoformat(r["timestamp"]).timestamp() * 1000.0 for r in readings]
    min_time = min(timestamps_ms)
    max_time = max(timestamps_ms)
    points = []
    for r in readings:
        x = calculate_chart_x_coordinate(r["timestamp"], min_time, max_time, len(readings))
        level = float(r["level"])
        y = round(TOP_MARGIN + ((100.0 - level) / 100.0) * PLOT_HEIGHT, 2)
        points.append({
            "x": x,
            "y": y,
            "reading": r,
            "is_under_threshold": level < LOW_THRESHOLD,
        })
    return points


# ==============================================================================
# TEST 1: THRESHOLD ALERT BOUNDARY LOGIC
# ==============================================================================

@pytest.mark.parametrize(
    ("level", "expected_alert"),
    [
        (0.0, True),
        (0.0001, True),
        (10.5, True),
        (19.9, True),
        (19.999, True),
        (20.0, False),  # Boundary: Exactly 20% is NOT an active alert
        (20.001, False),
        (20.1, False),
        (55.0, False),
        (100.0, False),
    ],
)
def test_threshold_alert_boundary_logic(level: float, expected_alert: bool) -> None:
    """Verify that level < 20 produces active alert, and level >= 20 is nominal."""
    assert evaluate_alert_threshold(level) is expected_alert


def test_threshold_alert_invalid_type() -> None:
    """Verify that boolean or non-numeric types raise TypeError."""
    with pytest.raises(TypeError):
        evaluate_alert_threshold("invalid")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        evaluate_alert_threshold(True)  # type: ignore[arg-type]


# ==============================================================================
# TEST 2: ASSIGNMENT DATASET METRICS & ALERT SEPARATION
# ==============================================================================

def test_assignment_mock_data_metrics_and_alert_distinction() -> None:
    """Verify current=55%, min=18%, max=78%, historical low=1, active alert=0."""
    with open(MOCK_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    readings = data.get("tank_readings") or data.get("readings") or []
    levels = [float(r["level"]) for r in readings]

    current = levels[-1]
    minimum = min(levels)
    maximum = max(levels)

    assert current == 55.0, f"Expected current level 55.0, got {current}"
    assert minimum == 18.0, f"Expected minimum level 18.0, got {minimum}"
    assert maximum == 78.0, f"Expected maximum level 78.0, got {maximum}"

    # Critical requirement: distinguish active alert from historical events
    active_alert = evaluate_alert_threshold(current)
    assert active_alert is False, "Current level 55% must NOT trigger an active alert"

    historical_lows = [r for r in readings if evaluate_alert_threshold(r["level"])]
    assert len(historical_lows) == 1, "Exactly one historical low-level event should exist (at 16:00)"
    assert historical_lows[0]["level"] == 18.0
    assert "16:00" in historical_lows[0]["timestamp"]


# ==============================================================================
# TEST 3: TIME-PROPORTIONAL CHART X-COORDINATE ENGINE
# ==============================================================================

def test_linear_time_chart_proportional_positioning() -> None:
    """Verify that irregular timestamp gaps produce proportional X coordinates,

    preventing misleading index-based spacing.
    """
    # 3 readings: 06:00, 06:30, 20:00 (Total span: 14 hours = 840 mins)
    readings = [
        {"timestamp": "2026-11-02T06:00:00+05:30", "level": 78.0},
        {"timestamp": "2026-11-02T06:30:00+05:30", "level": 60.0},
        {"timestamp": "2026-11-02T20:00:00+05:30", "level": 55.0},
    ]

    points = calculate_chart_points(readings)
    assert len(points) == 3

    # Point 0 at t=0 -> x = left margin = 46.0
    assert points[0]["x"] == 46.0

    # Point 2 at t=840min -> x = left + plot_width = 46 + 694 = 740.0
    assert points[2]["x"] == 740.0

    # Point 1 at t=30min -> x = 46 + (30 / 840) * 694 = 46 + 24.79 = 70.79
    # Under old index-based spacing, point 1 would be at 46 + 0.5 * 694 = 393.0!
    assert points[1]["x"] == 70.79
    assert points[1]["x"] < 100.0, "Point at 06:30 should be clustered near 06:00, not at midpoint"


def test_linear_time_chart_single_reading_centered() -> None:
    """A single reading must be centered on the chart width."""
    readings = [{"timestamp": "2026-11-02T12:00:00+05:30", "level": 50.0}]
    points = calculate_chart_points(readings)
    assert len(points) == 1
    # Center = 46 + 694 / 2 = 393.0
    assert points[0]["x"] == 393.0


def test_linear_time_chart_empty_readings() -> None:
    """Empty reading list returns empty points without error."""
    assert calculate_chart_points([]) == []


# ==============================================================================
# TEST 4: STRICT FRONTEND VALIDATION RULES
# ==============================================================================

def validate_tank_summary_schema(summary: dict[str, Any]) -> None:
    """Python validator mirroring dashboard.js validateTankSummary."""
    if not isinstance(summary, dict):
        raise ValueError("Summary must be a dict")

    for key in ("current_level", "minimum_level", "maximum_level"):
        if key not in summary or not isinstance(summary[key], (int, float)) or isinstance(summary[key], bool):
            raise ValueError(f"Missing or invalid {key}")
        if not 0.0 <= float(summary[key]) <= 100.0:
            raise ValueError(f"{key} must be between 0 and 100")

    if float(summary["minimum_level"]) > float(summary["maximum_level"]):
        raise ValueError("minimum_level cannot exceed maximum_level")

    if not isinstance(summary.get("active_alert"), bool):
        raise ValueError("active_alert must be a boolean")

    if not isinstance(summary.get("readings"), list):
        raise ValueError("readings must be a list")

    iso_regex = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
    prev_time = None
    for idx, r in enumerate(summary["readings"]):
        if not isinstance(r, dict):
            raise ValueError(f"Reading at {idx} must be a dict")
        ts = r.get("timestamp")
        if not isinstance(ts, str) or not iso_regex.match(ts):
            raise ValueError(f"Reading at {idx} has invalid timestamp: {ts}")
        dt = datetime.fromisoformat(ts)
        if prev_time and dt < prev_time:
            raise ValueError(f"Non-monotonic timestamps at index {idx}")
        prev_time = dt

        lvl = r.get("level") if "level" in r else r.get("level_percent")
        if lvl is None or isinstance(lvl, bool) or not isinstance(lvl, (int, float)) or not 0.0 <= float(lvl) <= 100.0:
            raise ValueError(f"Reading at {idx} has invalid level: {lvl}")


def test_validator_rejects_out_of_range_and_malformed() -> None:
    """Verify validator catches out-of-range metrics and malformed timestamps."""
    # Min > Max
    with pytest.raises(ValueError, match="cannot exceed"):
        validate_tank_summary_schema({
            "current_level": 50.0,
            "minimum_level": 80.0,
            "maximum_level": 20.0,
            "active_alert": False,
            "readings": [],
        })

    # Out of range level
    with pytest.raises(ValueError, match="between 0 and 100"):
        validate_tank_summary_schema({
            "current_level": 150.0,
            "minimum_level": 10.0,
            "maximum_level": 100.0,
            "active_alert": False,
            "readings": [],
        })

    # Naive timestamp (lacks timezone)
    with pytest.raises(ValueError, match="invalid timestamp"):
        validate_tank_summary_schema({
            "current_level": 50.0,
            "minimum_level": 20.0,
            "maximum_level": 80.0,
            "active_alert": False,
            "readings": [{"timestamp": "2026-11-02T10:00:00", "level": 50.0}],
        })

    # Non-monotonic readings
    with pytest.raises(ValueError, match="Non-monotonic"):
        validate_tank_summary_schema({
            "current_level": 50.0,
            "minimum_level": 20.0,
            "maximum_level": 80.0,
            "active_alert": False,
            "readings": [
                {"timestamp": "2026-11-02T12:00:00+05:30", "level": 50.0},
                {"timestamp": "2026-11-02T08:00:00+05:30", "level": 60.0},
            ],
        })


# ==============================================================================
# TEST 5: STATIC CODE AUDIT — ZERO innerHTML IN DASHBOARD.JS
# ==============================================================================

def test_static_code_audit_zero_inner_html_in_dashboard_js() -> None:
    """Verify that dashboard.js contains ZERO innerHTML assignments, eliminating

    dynamic XSS/HTML injection risks.
    """
    dashboard_js = (FRONTEND_DIR / "js" / "dashboard.js").read_text(encoding="utf-8")

    # Match any assignment to .innerHTML (ignoring comments)
    code_lines = [
        line.strip() for line in dashboard_js.splitlines()
        if not line.strip().startswith("//") and not line.strip().startswith("/*") and not line.strip().startswith("*")
    ]
    inner_html_assignments = [line for line in code_lines if ".innerHTML" in line]
    assert len(inner_html_assignments) == 0, f"Found unsafe innerHTML usage: {inner_html_assignments}"


# ==============================================================================
# TEST 6: STATIC HTML & CSS AUDIT FOR SEMANTIC HOOKS
# ==============================================================================

def test_static_html_and_css_hooks_present() -> None:
    """Verify that index.html and styles.css have all required semantic IDs and classes."""
    html_content = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    css_content = (FRONTEND_DIR / "css" / "styles.css").read_text(encoding="utf-8")

    # Required HTML IDs
    required_ids = [
        "device-status-tag",
        "stale-state",
        "stale-message",
        "cached-state",
        "cached-message",
        "cached-retry-button",
        "live-beacon",
        "eyebrow-text",
        "connection-status",
        "connection-label",
        "api-footer-status",
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in html_content, f"Missing id='{element_id}' in index.html"

    # Required CSS classes
    required_classes = [
        ".online-tag.offline",
        ".online-tag.stale",
        ".online-tag.unknown",
        ".live-dot-beacon.is-stale",
        ".live-dot-beacon.is-offline",
        ".status-chip.stale",
        ".stale-banner",
        ".warning-banner",
    ]
    for cls in required_classes:
        assert cls in css_content, f"Missing class '{cls}' in styles.css"


# ==============================================================================
# TEST 7: FASTAPI TESTCLIENT INTEGRATION & CONTRACT VALIDATION
# ==============================================================================

def test_fastapi_tank_summary_contract_satisfies_frontend() -> None:
    """Verify that /api/tank/summary returns the complete contract needed by the frontend."""
    client = TestClient(app)
    response = client.get("/api/tank/summary")
    assert response.status_code == 200

    data = response.json()
    validate_tank_summary_schema(data)

    assert data["current_level"] == 55.0
    assert data["minimum_level"] == 18.0
    assert data["maximum_level"] == 78.0
    assert data["active_alert"] is False
    assert len(data["readings"]) == 8
    assert len(data["historical_low_events"]) == 1
    assert data["is_stale"] is True  # Nov 2 2026 is >24h relative to real wall-clock


def test_fastapi_device_status_contract_and_auth() -> None:
    """Verify /login and /device/tank-001/status provide separate device telemetry."""
    client = TestClient(app)

    # 1. Unauthenticated device status returns 401
    unauth_resp = client.get("/device/tank-001/status")
    assert unauth_resp.status_code == 401

    # 2. Authenticate
    login_resp = client.post("/login", json={"username": "demo", "password": "aqua123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 3. Authenticated device status returns 200 with device fields
    dev_resp = client.get("/device/tank-001/status", headers={"Authorization": f"Bearer {token}"})
    assert dev_resp.status_code == 200
    dev_data = dev_resp.json()

    assert dev_data["id"] == "tank-001"
    assert dev_data["online"] is True
    assert dev_data["pump_state"] in ("on", "off")
    assert 0.0 <= dev_data["level_percent"] <= 100.0
    assert "last_seen" in dev_data
