# AquaSense - Baseline Assessment & QA Report (Phase 0)

**Date**: 2026-11-04  
**Audit Stage**: Phase 0 Baseline Verification  
**Evaluation Scope**: Environment, Runtime, Endpoints, Capabilities, Test Metrics, and Deployment Topology  

---

## 1. Existing Project Capabilities

AquaSense provides the following functional capabilities in its baseline state:

- **Telemetry Summary Aggregation**: Ingests, parses, and chronologically sorts mock tank sensor readings to compute current liquid level, operational minimum, and operational maximum.
- **Safety Floor Monitoring**: Enforces a fixed 20% critical volume threshold; flags active alerts if the latest reading breaches this floor and logs previous threshold violations into an audit history.
- **Device Health Auditing**: Tracks IoT device connectivity states (`online`, `offline`, `stale`) based on an internal 24-hour inactivity timeout (`STALE_AFTER_SECONDS = 86400`).
- **Mock Token Authentication**: Implements HTTP Bearer authentication for protected device inspection endpoints using configurable environment variables or default mock credentials (`demo` / `aqua123`).
- **Interactive Single-Page Dashboard**:
  - Atmospheric Welcome Splash screen with animated wave crests, bubble particles, and auto-entry countdown.
  - Dual visualizers: Conic radial gauge and vertical liquid cylinder with dynamic water fill and oscillating surface waves.
  - Interactive SVG historical trend chart with hover tooltips displaying sample timestamps and levels.
  - Dark Oceanic Midnight and Light Marine theme toggle with persistent state in `localStorage`.
  - Automatic polling cycle updating data every 25 seconds during active browser visibility.

---

## 2. Environment & Dependency Versions

All tools and packages have been verified against the active virtual environment on Windows 11:

| Component / Library | Active Version | Purpose |
|---|---|---|
| **Python Runtime** | `3.15.2` (64-bit Windows) | Core language runtime (`.\.venv\Scripts\python.exe`) |
| **FastAPI** | `0.162.0` | Asynchronous Web API framework |
| **Uvicorn** | `0.54.0` | ASGI web server implementation |
| **Pydantic** | `2.14.2` | Data validation and schema enforcement |
| **Pydantic Core** | `2.50.2` | High-performance Rust backend for Pydantic |
| **Starlette** | `1.10.0` | ASGI toolkit underneath FastAPI |
| **HTTPX** | `0.28.1` | Next-generation HTTP client utilized by `TestClient` |
| **Pytest** | `9.2.0` | Automated unit and integration test runner |
| **AnyIO** | `4.16.0` | Asynchronous networking library |

---

## 3. Existing API Endpoints Specification

| Method | Route | Authentication | Request Model | Response Model / Structure | Status Codes |
|---|---|:---:|---|---|:---:|
| `GET` | `/` | None | N/A | Static HTML (`frontend/index.html`) | `200` |
| `GET` | `/health` | None | N/A | `{"status": "ok"}` | `200` |
| `GET` | `/api` | None | N/A | `{"message": str, "status": str, "docs": str}` | `200` |
| `POST` | `/login` | None | `LoginRequest` (`username`, `password`) | `LoginResponse` (`access_token`, `token_type`) | `200`, `401`, `422` |
| `GET` | `/api/tank/summary` | None | N/A | `TankSummary` (`current_level`, `min`, `max`, `readings`, etc.) | `200`, `500` |
| `GET` | `/device/{device_id}/status` | **Bearer Token** | Route parameter `device_id` | `DeviceStatus` (`id`, `online`, `last_seen`, `is_stale`, `status`) | `200`, `401`, `404`, `500`, `503` |
| `GET` | `/docs` | None | N/A | Interactive Swagger UI | `200` |
| `GET` | `/openapi.json` | None | N/A | OpenAPI JSON schema specification | `200` |

---

## 4. Existing Test Suite Execution & Results

The test suite was executed against the baseline codebase without modification:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Actual Terminal Execution Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.15.2, pytest-9.2.0, pluggy-1.7.0 -- D:\AquaSense\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\AquaSense
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.16.0
collecting ... collected 16 items

tests/test_device_status.py::test_device_status_valid_token PASSED       [  6%]
tests/test_device_status.py::test_device_status_invalid_token PASSED     [ 12%]
tests/test_device_status.py::test_device_status_missing_token PASSED     [ 18%]
tests/test_device_status.py::test_device_status_nonexistent_device PASSED [ 25%]
tests/test_device_status.py::test_device_status_offline_device PASSED    [ 31%]
tests/test_device_status.py::test_device_status_malformed_record PASSED  [ 37%]
tests/test_device_status.py::test_device_status_malformed_timestamp PASSED [ 43%]
tests/test_device_status.py::test_device_status_stale_timestamp PASSED   [ 50%]
tests/test_login.py::test_login_success PASSED                           [ 56%]
tests/test_login.py::test_login_invalid_password PASSED                  [ 62%]
tests/test_login.py::test_login_missing_fields PASSED                    [ 68%]
tests/test_tank_levels.py::test_tank_level_boundary_zero_percent_accepted PASSED [ 75%]
tests/test_tank_levels.py::test_tank_level_boundary_hundred_percent_accepted PASSED [ 81%]
tests/test_tank_levels.py::test_tank_level_boundary_below_zero_rejected PASSED [ 87%]
tests/test_tank_levels.py::test_tank_level_boundary_above_hundred_rejected PASSED [ 93%]
tests/test_tank_levels.py::test_tank_reading_model_boundary_validation PASSED [100%]

============================= 16 passed in 1.00s ==============================
```

### Metrics:
- **Total Tests**: 16
- **Passed**: 16 (100%)
- **Failed**: 0
- **Duration**: 1.00 second
- **Warnings**: 0 (cleanly filtered via `pytest.ini`)

---

## 5. Current Deployment Topology

- **Vercel Serverless Function**: Configured via `api/index.py` and `vercel.json` utilizing `@vercel/python` runtime.
- **Edge Routing & CDN**:
  - API and OpenAPI documentation routes (`/api/*`, `/health`, `/login`, `/device/*`, `/docs`) are rewritten to the serverless Python ASGI function.
  - Frontend static assets (`/`, `/css/*`, `/js/*`) are served directly from Vercel's global Edge CDN.
- **Local Development**: Runs via `uvicorn backend.app.main:app --reload` on port 8000, serving the embedded frontend from disk.

---

## 6. Known Baseline Limitations

1. **Static Mock Dataset**: Data is read-only from `data/mock_data.json`; no dynamic telemetry ingestion or write mutations are supported.
2. **Fragile Time Invariance**: Tests currently pass only because `mock_data.json` matches today's date (`2026-11-04`); tests lack simulated time freezing.
3. **No Dynamic Device Telemetry Binding**: The frontend does not query `/device/{id}/status`, leaving hardware connection state decoupled from API reachability.
4. **Uniform Chart Interval Spacing**: The SVG historical chart calculates X-coordinates based on reading array index rather than real elapsed time.

