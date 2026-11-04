# AquaSense - Comprehensive Technical Project Audit (Phase 0)

**Date**: 2026-11-04  
**Audit Phase**: Phase 0 (Strict Inspection and Baseline Analysis)  
**Auditor**: Senior Software Engineer / Lead QA Reviewer  
**Status**: Completed — Ready for Review prior to Phase 1 Execution  

---

## 1. Existing System Architecture

AquaSense is structured as a decoupled two-tier architecture comprised of a FastAPI asynchronous REST microservice backend and a client-side single-page dashboard (SPA) served via static file mounting or edge CDN rewrites.

```
+-----------------------------------------------------------------------+
|                              CLIENT TIER                              |
|                                                                       |
|   +---------------------------------------------------------------+   |
|   |                      Browser / Web View                       |   |
|   |   - Welcome Splash / Auto-Enter Countdown                     |   |
|   |   - Dual Visualizers: Conic Arc Gauge + Dynamic Wave Tank     |   |
|   |   - SVG Time-Series Chart + Hover Tooltips                    |   |
|   |   - Active Incident Banner & Historical Audit Log             |   |
|   |   - Theme Manager (Oceanic Dark / Marine Light)               |   |
|   +-------------------------------+-------------------------------+   |
|                                   |                                   |
|                          HTTP / JSON Polling                          |
|                         (every 25s / on-demand)                       |
+-----------------------------------|-----------------------------------+
                                    |
+-----------------------------------|-----------------------------------+
|                              SERVER TIER                              |
|                                   v                                   |
|   +---------------------------------------------------------------+   |
|   |                    FastAPI (ASGI / Uvicorn)                   |   |
|   |   - CORS Middleware (Localhost + *.vercel.app)                |   |
|   |   - HTTP Bearer Authentication Guard                          |   |
|   |   - StaticFiles Catch-All Mount (at /)                        |   |
|   +---------------+-------------------------------+---------------+   |
|                   |                               |                   |
|                   v                               v                   |
|   +-------------------------------+ +-----------------------------+   |
|   |       Device Controller       | |      Telemetry Service      |   |
|   |  - GET /device/{id}/status    | |  - GET /api/tank/summary    |   |
|   |  - Stale / Offline Logic      | |  - Validation & Aggregation |   |
|   +---------------+---------------+ +-------------+---------------+   |
|                   |                               |                   |
|                   +---------------+---------------+                   |
|                                   |                                   |
|                                   v                                   |
|   +---------------------------------------------------------------+   |
|   |                      Data Access Layer                        |   |
|   |   - backend/app/data.py (File IO & Schema Guards)             |   |
|   |   - data/mock_data.json (IoT Devices & Readings Array)        |   |
|   +---------------------------------------------------------------+   |
+-----------------------------------------------------------------------+
```

---

## 2. Component & Workflow Analysis

### 2.1 Backend Request Flow
1. **Request Intake**: Incoming HTTP requests hit FastAPI via Uvicorn (local) or `api/index.py` (Vercel Serverless Function).
2. **CORS Evaluation**: Requests pass through `CORSMiddleware` matching `http://localhost:*`, `http://127.0.0.1:*`, or `https://*.vercel.app`.
3. **Route Dispatching**:
   - `GET /` -> Serves `frontend/index.html` via `StaticFiles`.
   - `GET /health` -> Lightweight health check (`{"status": "ok"}`).
   - `GET /api` -> Service status metadata.
   - `POST /login` -> Validates JSON body against `LoginRequest` Pydantic model and returns `LoginResponse`.
   - `GET /device/{device_id}/status` -> Protected by `bearer_scheme`. Validates token against `MOCK_TOKEN`. Reads device record from `data/mock_data.json`.
   - `GET /api/tank/summary` -> Calls `_validated_readings()`, parses array into `TankReading` Pydantic models, sorts by timestamp, and computes aggregates.

### 2.2 Frontend Execution Flow
1. **DOM Bootstrap**: `index.html` loads with `data-theme="dark"`. `styles.css` renders layout.
2. **Welcome Experience**: `#welcome-screen` renders as a fixed overlay with animated water waves, floating particles, and a 3-second auto-entry countdown.
3. **Dismissal & Transition**: On button click, timeout, or Space/Enter keypress, `dismissWelcomeScreen()` applies class `.is-leaving` and displays the dashboard with staggered viewport reveals (`.reveal.is-visible`).
4. **Data Acquisition (`loadDashboard()`)**:
   - Requests `GET /api/tank/summary` with a 10-second `AbortController` timeout.
   - If successful, renders capacity dial, wave cylinder height (`--tank-liquid-fill`), statistical cards, SVG chart, and incident list.
   - If failed, reveals `#error-state` banner with retry trigger.
5. **Periodic Telemetry Polling**: An interval executes `loadDashboard()` every 25 seconds when the document visibility state is `visible`.

### 2.3 Authentication Mechanism
- Implemented in `backend/app/auth.py`.
- Utilizes `HTTPBearer(auto_error=False)` from `fastapi.security`.
- Credentials configurable via environment variables with hardcoded fallbacks:
  - `AQUASENSE_USERNAME` (default: `"demo"`)
  - `AQUASENSE_PASSWORD` (default: `"aqua123"`)
  - `AQUASENSE_TOKEN` (default: `"aquasense-demo-token"`)
- Authentication function `require_token` performs strict string comparison against `MOCK_TOKEN`.

### 2.4 Data Processing & Telemetry Math
- In `backend/app/data.py`:
  - `load_data()` opens and decodes `data/mock_data.json`.
  - `tank_readings()` ensures readings exist and levels satisfy `0 <= level <= 100`.
- In `backend/app/main.py`:
  - `_validated_readings()` parses dicts into `TankReading` models and sorts: `sorted(readings, key=lambda reading: reading.timestamp)`.
  - `current_level = readings[-1].level` (assumes last element after sort is the authoritative active reading).
  - `minimum_level = min(reading.level for reading in readings)`.
  - `maximum_level = max(reading.level for reading in readings)`.
  - `active_alert = current < LOW_LEVEL_THRESHOLD` (where threshold is 20%).
  - `historical_low_events = [r for r in readings if r.level < 20]`.

### 2.5 Test Architecture
- Test framework: `pytest 9.2.0` with `fastapi.testclient.TestClient`.
- Test configuration: `pytest.ini` with testpaths = `tests` and warning filters.
- Test suites:
  - `tests/test_login.py` (3 test cases: success, invalid password, missing fields).
  - `tests/test_device_status.py` (8 test cases: valid token, invalid token, missing token, nonexistent device, offline device, malformed record, malformed timestamp, stale timestamp).
  - `tests/test_tank_levels.py` (5 test cases: 0% boundary, 100% boundary, <0% rejected, >100% rejected, Pydantic model validation).

---

## 3. Comprehensive Audit Findings & Deficiencies

### Priority A Issues (Mandatory Fixes Identified Before Submission)

#### Issue 1: Acceptance of Future Device and Reading Timestamps
- **File Reference**: `backend/app/main.py#L96-L104`, `backend/app/data.py#L44-L55`
- **Symptom**: If an IoT device clock skews or submits a timestamp in the future (e.g. `2099-01-01T00:00:00Z`), `age_seconds` is negative (`-2,000,000,000s`).
- **Impact**: `age_seconds > STALE_AFTER_SECONDS` evaluates to `False`. The device is incorrectly reported as `online: true` and `is_stale: false`. For tank readings, future timestamps sort to the end of the array, masquerading as the "current" live reading.
- **Root Cause**: Missing validation `if last_seen > now:` and absence of timestamp freshness bounds on telemetry ingestion.

#### Issue 2: Timezone Inconsistencies & Offset-Naive Crashes
- **File Reference**: `backend/app/main.py#L60-L66`, `backend/app/models.py#L17-L19`
- **Symptom**: `TankReading.timestamp` accepts arbitrary ISO strings. If one reading is offset-aware (`+05:30`) and another is offset-naive (`2026-11-04T12:00:00`), `sorted(readings, key=lambda r: r.timestamp)` raises an unhandled `TypeError: can't compare offset-naive and offset-aware datetimes`.
- **Impact**: Server 500 crashes on mixed timezone inputs. Additionally, naive timestamps sent to the browser via JSON cause client-side `new Date(value)` to interpret them in browser local time rather than device/UTC time.
- **Root Cause**: Lack of explicit timezone normalization (e.g. coercing naive datetimes to UTC or consistent offsets in Pydantic validators).

#### Issue 3: Stale Readings Appearing as "Live" Telemetry
- **File Reference**: `backend/app/main.py#L107-L120`, `frontend/index.html#L237-L244`, `frontend/js/dashboard.js#L232-L282`
- **Symptom**: If the latest reading in `data/mock_data.json` is weeks or months old, `GET /api/tank/summary` still returns it as `current_level`, and the UI labels it "Live reservoir capacity" with a pulsing green indicator.
- **Impact**: Operators are misled into believing inactive or dead sensors represent real-time physical conditions.
- **Root Cause**: `TankSummary` does not calculate telemetry age, nor does it flag `is_reading_stale`. The frontend does not differentiate between "latest reading recorded" and "live data currently streaming".

#### Issue 4: Inadequate Frontend Response Validation
- **File Reference**: `frontend/js/dashboard.js#L491-L498`
- **Symptom**: The response validator only checks `Number.isFinite` on summary aggregates and `Array.isArray(summary.readings)`. It does NOT validate individual reading objects inside the array.
- **Impact**: If a reading entry has `{ "level": null }` or `{ "timestamp": "corrupt" }`, `Number(reading.level)` produces `NaN`, injecting corrupt SVG coordinates into the DOM and breaking chart rendering silently.
- **Root Cause**: Shallow client-side schema verification.

#### Issue 5: Blurring of API Connectivity vs Device Connectivity
- **File Reference**: `frontend/index.html#L141-L144`, `frontend/index.html#L205-L210`, `frontend/js/dashboard.js#L200-L205`
- **Symptom**: The topbar status pill `#connection-status` displays "Connected" with a green beacon whenever `GET /api/tank/summary` returns HTTP 200. Concurrently, the tank card displays a hardcoded static badge `<span class="online-tag">Online</span>`.
- **Impact**: If the physical device `tank-001` is OFFLINE (HTTP 503) or STALE, the dashboard still tells the user "Connected" and "Online" simply because the web server is reachable. The frontend never queries `GET /device/tank-001/status`.
- **Root Cause**: Failure to decouple microservice reachability from IoT field device state.

#### Issue 6: Chart Positioning Uses Index Instead of Timestamp Proportions
- **File Reference**: `frontend/js/dashboard.js#L396-L400`
- **Symptom**: SVG X-coordinates are plotted via:
  `x = left + (index / (readings.length - 1)) * plotWidth;`
- **Impact**: A 2-hour interval (14:00 to 16:00) occupies the exact same horizontal distance as a 1-hour interval (16:00 to 17:00). Irregularly spaced readings distort visual slope and rate of consumption.
- **Root Cause**: Array index interpolation instead of linear temporal interpolation:
  `x = left + ((t - t_min) / (t_max - t_min)) * plotWidth`.

#### Issue 7: Time-Dependent Automated Test Fragility
- **File Reference**: `tests/test_device_status.py#L13-L24`, `data/mock_data.json#L6`
- **Symptom**: `test_device_status_valid_token` asserts `body["is_stale"] is False` against hardcoded mock data `"last_seen": "2026-11-04T12:00:00+05:30"`.
- **Impact**: In exactly 24 hours from the mock timestamp, `(datetime.now() - last_seen).total_seconds()` will exceed 86,400s, turning `is_stale` to `True`. The test suite will fail automatically without any code changes.
- **Root Cause**: Reliance on system wall clock without time mocking (`unittest.mock.patch` on `datetime` or dynamic timestamp fixtures).

#### Issue 8: Placeholder URL in README
- **File Reference**: `README.md#L115`
- **Symptom**: Contains `git clone https://github.com/your-username/AquaSense.git`.
- **Impact**: Unusable clone instructions for end users.
- **Root Cause**: Unreplaced repository template placeholder.

#### Issue 9: AI and Test Execution Documentation Discrepancies
- **File Reference**: `docs/ai_usage.md`, `docs/test-cases.md`
- **Symptom**: Test execution dates and initial failure narratives require exact synchronization with all test files and verified run parameters.
- **Impact**: Inaccurate compliance documentation.
- **Root Cause**: Incremental additions without consolidated cross-referencing.

#### Issue 10: Mobile Testing Documentation Divergence from Actual API
- **File Reference**: `docs/mobile_testing.md#L3`
- **Symptom**: The mobile disconnection specification describes in-flight operations such as *"valve controls or threshold modifications"*, *"idempotency keys (UUIDv4)"*, and *"server-side audit logs for deduplicating hardware actuation"*.
- **Impact**: Disconnect between documented requirements and actual system capabilities, as the backend currently only exposes read-only telemetry and mock login endpoints.
- **Root Cause**: Speculative architectural narrative not grounded in the actual codebase API scope.

---

### Additional Quality & Maintainability Observations

1. **Hardcoded Device Staleness Window**:
   - `STALE_AFTER_SECONDS = 24 * 60 * 60` is hardcoded in `backend/app/main.py#L35`. Should be configurable via environment variable `AQUASENSE_STALE_SECONDS`.
2. **Coupled Device Selection**:
   - The device identifier `tank-001` is hardcoded across `frontend/index.html` and `dashboard.js`. Multi-device switching is UI-only without dynamic binding.
3. **Missing Read-Write Data Mutation API**:
   - Mock data can only be modified by altering the underlying JSON file directly; no endpoints exist to ingest new readings.

---

## 4. Recommended Implementation Strategy & Priorities

| Priority | Phase | Action Item | Target Files |
|---|:---:|---|---|
| **High** | 1 | **Temporal Integrity & Validation**<br>- Reject future timestamps (`last_seen > now`).<br>- Normalize timezones to UTC across Pydantic models.<br>- Prevent stale readings from masquerading as live. | `backend/app/models.py`<br>`backend/app/main.py`<br>`backend/app/data.py` |
| **High** | 1 | **Deterministic Test Suite**<br>- Mock system time in `test_device_status.py` so tests never fail due to calendar progression.<br>- Add tests for future timestamp rejection and timezone consistency. | `tests/test_device_status.py`<br>`tests/test_tank_levels.py` |
| **High** | 2 | **Frontend Precision & Decoupling**<br>- Decouple API connectivity from device connectivity.<br>- Query `GET /device/{id}/status` and display actual hardware state.<br>- Fix chart interpolation to plot linearly by timestamp.<br>- Implement deep response schema validation. | `frontend/js/dashboard.js`<br>`frontend/index.html`<br>`frontend/css/styles.css` |
| **Medium** | 3 | **Documentation Grounding & Polish**<br>- Replace GitHub placeholder in `README.md`.<br>- Align `mobile_testing.md` with realistic read-only telemetry architecture.<br>- Synchronize `test-cases.md` and `ai_usage.md`. | `README.md`<br>`docs/mobile_testing.md`<br>`docs/test-cases.md`<br>`docs/ai_usage.md` |
| **Low** | 4 | **Configurability**<br>- Make staleness window configurable via environment variables. | `backend/app/main.py` |

---

## 5. Phase 0 Audit Conclusion

The application demonstrates strong foundational code quality, clean UI presentation, and passing baseline tests. However, critical vulnerabilities regarding **time dependency, temporal validation, chart linearity, and device-vs-API state conflation** require remediation before final production submission.

