# AquaSense - Automated Test Cases & QA Verification Register

This document provides a record of all **92 automated test cases** designed, executed, and verified for the AquaSense platform. All tests run deterministically against the FastAPI backend, Pydantic schemas, and frontend mathematical engines without requiring physical IoT sensors or external cloud dependencies.

---

## 1. Test Execution Summary

- **Total Test Cases**: 92
- **Passed**: 92 (100%)
- **Failed**: 0
- **Skipped**: 0
- **Backend Code Coverage**: 100% (213/213 statements)
- **Execution Date**: 2026-11-04
- **Test Harness**: `pytest` 9.2.0, `pytest-cov` 7.1.0, `FastAPI TestClient` (Starlette/HTTPX) on Python 3.15.2 (Windows 11)

---

## 2. Category 1: User Authentication (`tests/test_login.py`)

| Test ID | Test Description | Preconditions | Input (Method, URL, Body) | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-AUTH-001** | Successful login with valid credentials | FastAPI server running with mock auth | `POST /login`<br>`{"username": "demo", "password": "aqua123"}` | `200 OK`, `access_token: "aquasense-demo-token"`, `token_type: "bearer"` | `200 OK`, valid bearer token returned | **PASS** |
| **TC-AUTH-002** | Login failure with invalid password | Server running | `POST /login`<br>`{"username": "demo", "password": "wrongpassword"}` | `401 Unauthorized`<br>`{"detail": "Invalid username or password"}` | `401 Unauthorized`, WWW-Authenticate header set | **PASS** |
| **TC-AUTH-003** | Login failure with invalid username | Server running | `POST /login`<br>`{"username": "unknown_operator", "password": "aqua123"}` | `401 Unauthorized`<br>`{"detail": "Invalid username or password"}` | `401 Unauthorized`, exact error message | **PASS** |
| **TC-AUTH-004** | Missing username field | Server running | `POST /login`<br>`{"password": "aqua123"}` | `422 Unprocessable Entity`<br>Location `["body", "username"]` | `422 Unprocessable Entity`, location verified | **PASS** |
| **TC-AUTH-005** | Missing password field | Server running | `POST /login`<br>`{"username": "demo"}` | `422 Unprocessable Entity`<br>Location `["body", "password"]` | `422 Unprocessable Entity`, location verified | **PASS** |
| **TC-AUTH-006** | Empty object payload | Server running | `POST /login`<br>`{}` | `422 Unprocessable Entity`<br>Validation errors for both fields | `422 Unprocessable Entity`, both fields flagged | **PASS** |
| **TC-AUTH-007** | Empty string username (`""`) | Server running | `POST /login`<br>`{"username": "", "password": "aqua123"}` | `422 Unprocessable Entity`<br>Violates `min_length=1` | `422 Unprocessable Entity`, min_length enforced | **PASS** |
| **TC-AUTH-008** | Empty string password (`""`) | Server running | `POST /login`<br>`{"username": "demo", "password": ""}` | `422 Unprocessable Entity`<br>Violates `min_length=1` | `422 Unprocessable Entity`, min_length enforced | **PASS** |
| **TC-AUTH-009** | Malformed data types (int/null) | Server running | `POST /login`<br>`{"username": 12345, "password": null}` | `422 Unprocessable Entity`<br>Type mismatch errors | `422 Unprocessable Entity`, type errors flagged | **PASS** |
| **TC-AUTH-010** | Non-string username (array) | Server running | `POST /login`<br>`{"username": ["demo"], "password": "aqua123"}` | `422 Unprocessable Entity`<br>String constraint violation | `422 Unprocessable Entity`, array rejected | **PASS** |
| **TC-AUTH-011** | Raw non-JSON payload | Server running | `POST /login`<br>`Content: "raw-unformatted-string"` | `422 Unprocessable Entity`<br>Invalid JSON decoding | `422 Unprocessable Entity`, raw text rejected | **PASS** |

---

## 3. Category 2: Device Hardware Telemetry (`tests/test_device_status.py`)

| Test ID | Test Description | Preconditions | Input (Method, URL, Headers) | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-DEV-001** | Device status with valid token | Device `tank-001` fresh | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `200 OK`, `online: true`, `status: "online"`, `is_stale: false` | `200 OK`, `level_percent: 55.0`, `pump_state: "off"` | **PASS** |
| **TC-DEV-002** | Device status with invalid token | Server running | `GET /device/tank-001/status`<br>`Bearer invalid-token-xyz` | `401 Unauthorized`<br>`{"detail": "Invalid bearer token"}` | `401 Unauthorized`, detail verified | **PASS** |
| **TC-DEV-003** | Device status missing token | Server running | `GET /device/tank-001/status`<br>No auth header | `401 Unauthorized`<br>`{"detail": "Bearer token required"}` | `401 Unauthorized`, header enforced | **PASS** |
| **TC-DEV-004** | Nonexistent device ID | Server running | `GET /device/nonexistent-device-999/status`<br>`Bearer aquasense-demo-token` | `404 Not Found`<br>`{"detail": "Device not found"}` | `404 Not Found`, device not found | **PASS** |
| **TC-DEV-005** | Offline hardware device | Device `device-offline` with `online: false` | `GET /device/device-offline/status`<br>`Bearer aquasense-demo-token` | `503 Service Unavailable`<br>`{"detail": {"message": "Device is offline", "device_id": "device-offline"}}` | `503 Service Unavailable`, exact detail returned | **PASS** |
| **TC-DEV-006** | Malformed record (`online` not bool) | Device record has `"online": "not-a-bool"` | `GET /device/device-malformed/status`<br>`Bearer aquasense-demo-token` | `500 Internal Server Error`<br>`{"detail": "Device record is malformed"}` | `500 Internal Server Error`, malformed caught | **PASS** |
| **TC-DEV-007** | Malformed timestamp string | Device record has unparseable `last_seen` | `GET /device/device-bad-date/status`<br>`Bearer aquasense-demo-token` | `500 Internal Server Error`<br>`{"detail": "Device last_seen is malformed"}` | `500 Internal Server Error`, bad date caught | **PASS** |
| **TC-DEV-008** | Missing `last_seen` attribute | Device record omits `last_seen` | `GET /device/device-missing-last-seen/status`<br>`Bearer aquasense-demo-token` | `500 Internal Server Error`<br>`{"detail": "Device record is malformed"}` | `500 Internal Server Error`, missing key caught | **PASS** |
| **TC-DEV-009** | Stale device timestamp (>24h) | Device last seen 25 hours ago | `GET /device/device-stale/status`<br>`Bearer aquasense-demo-token` | `200 OK`, `is_stale: true`, `status: "stale"`, `online: true` | `200 OK`, correctly flagged stale | **PASS** |
| **TC-DEV-010** | Future timestamp beyond 5m tolerance | Device last seen 10m in future | `GET /device/device-future/status`<br>`Bearer aquasense-demo-token` | `400 Bad Request`<br>Contains `"future"` in detail | `400 Bad Request`, future drift rejected | **PASS** |
| **TC-DEV-011** | Future timestamp within 5m tolerance | Device last seen 2m in future | `GET /device/device-slight-future/status`<br>`Bearer aquasense-demo-token` | `200 OK`, `is_stale: false`, `online: true` | `200 OK`, clock drift tolerated | **PASS** |
| **TC-DEV-012** | Exact response contract schema | Device record with `level_percent: 72.5`, `pump_state: "on"` | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `200 OK`, exact key set: `{"id", "online", "status", "last_seen", "is_stale", "level_percent", "pump_state"}` | `200 OK`, all 7 keys and types validated | **PASS** |
| **TC-DEV-013** | Pump state validation ("on"/"off"/invalid) | Mocked records with pump states | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `"on"` -> 200, `"off"` -> 200, `"broken"` -> 500 | `200` for on/off, `500` for invalid | **PASS** |
| **TC-DEV-014** | Level percent boundaries (0, 100, -1, 100.5) | Mocked records with level percentages | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `0.0` -> 200, `100.0` -> 200, `-1.0` -> 500, `100.5` -> 500 | Boundaries accepted, out-of-range rejected | **PASS** |

---

## 4. Category 3: Tank Levels & Threshold Alerts (`tests/test_tank_levels.py`)

| Test ID | Test Description | Preconditions | Input (Method, URL, Payload) | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-LVL-001** | Level boundary 0% accepted | Mock reading at 0.0% | `GET /api/tank/summary` | `200 OK`, `current_level: 0.0`, `active_alert: true` | `200 OK`, alert raised | **PASS** |
| **TC-LVL-002** | Level boundary 100% accepted | Mock reading at 100.0% | `GET /api/tank/summary` | `200 OK`, `current_level: 100.0`, `active_alert: false` | `200 OK`, nominal state | **PASS** |
| **TC-LVL-003** | Level below 0% rejected (-1.0%) | Mock reading at -1.0% | `GET /api/tank/summary` | `500 Internal Server Error`<br>`detail: "Tank reading level must be between 0 and 100"` | `500 Internal Server Error`, rejected | **PASS** |
| **TC-LVL-004** | Level above 100% rejected (100.5%) | Mock reading at 100.5% | `GET /api/tank/summary` | `500 Internal Server Error`<br>`detail: "Tank reading level must be between 0 and 100"` | `500 Internal Server Error`, rejected | **PASS** |
| **TC-LVL-005** | Pydantic TankReading model boundary | Direct model instantiation | `TankReading(timestamp=..., level=-0.1)`<br>`TankReading(timestamp=..., level=100.1)` | Raises `pydantic.ValidationError` | `ValidationError` raised for both bounds | **PASS** |
| **TC-LVL-006** | Level boundary 19.9% active alert | Mock reading at 19.9% | `GET /api/tank/summary` | `200 OK`, `current_level: 19.9`, `active_alert: true`, historical count = 1 | `200 OK`, active alert triggered | **PASS** |
| **TC-LVL-007** | Level boundary 20.0% nominal | Mock reading at 20.0% | `GET /api/tank/summary` | `200 OK`, `current_level: 20.0`, `active_alert: false`, historical count = 0 | `200 OK`, nominal threshold maintained | **PASS** |
| **TC-LVL-008** | Level boundary 20.1% nominal | Mock reading at 20.1% | `GET /api/tank/summary` | `200 OK`, `current_level: 20.1`, `active_alert: false`, historical count = 0 | `200 OK`, nominal threshold maintained | **PASS** |
| **TC-LVL-009** | Empty reading history graceful handle | Mock empty `{"tank_readings": []}` | `GET /api/tank/summary` | `200 OK`, `current_level: 0.0`, `is_stale: true`, `latest_reading_timestamp: null` | `200 OK`, zeroed summary returned | **PASS** |
| **TC-LVL-010** | Malformed reading missing level | Reading dictionary omits `level` | `GET /api/tank/summary` | `500 Internal Server Error`<br>`detail: "Malformed tank reading"` | `500 Internal Server Error`, malformed caught | **PASS** |
| **TC-LVL-011** | Malformed reading non-numeric level | Reading has `"level": "seventy"` | `GET /api/tank/summary` | `500 Internal Server Error`<br>`detail: "Tank reading level must be between 0 and 100"` | `500 Internal Server Error`, non-numeric caught | **PASS** |
| **TC-LVL-012** | Historical event distinction | Prior 18%, current 55% | `GET /api/tank/summary` | `200 OK`, `current_level: 55.0`, `active_alert: false`, historical events = 1 | `200 OK`, active alert = false, historical = 1 | **PASS** |
| **TC-LVL-013** | Active alert with latest reading low | Prior 55%, current 18% | `GET /api/tank/summary` | `200 OK`, `current_level: 18.0`, `active_alert: true`, historical events = 1 | `200 OK`, active alert = true | **PASS** |

---

## 5. Category 4: Timestamps & Freshness (`tests/test_timestamps_and_freshness.py`)

| Test ID | Test Description | Preconditions | Input / Scenario | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-TIME-001** | Valid UTC ISO timestamp normalization | Direct helper call | Parse `"2026-11-04T10:00:00Z"` | UTC `datetime` with `hour=10`, `tzinfo=timezone.utc` | Timezone normalized to UTC | **PASS** |
| **TC-TIME-002** | Valid IST offset normalization | Direct helper call | Parse `"2026-11-04T15:30:00+05:30"` | UTC `datetime` with `hour=10` (15:30 - 5:30) | Normalized UTC hour = 10 | **PASS** |
| **TC-TIME-003** | Valid EDT offset normalization | Direct helper call | Parse `"2026-11-04T06:00:00-04:00"` | UTC `datetime` with `hour=10` (06:00 + 4:00) | Normalized UTC hour = 10 | **PASS** |
| **TC-TIME-004** | Mixed timezone chronological sorting | 3 readings (UTC, IST, EDT) | `GET /api/tank/summary` | Sorted in true chronological order by UTC time | Chronological ordering guaranteed | **PASS** |
| **TC-TIME-005** | Naive timestamp rejection | Naive string without offset | Parse `"2026-11-04T12:00:00"` | Raises `ValueError` ("Timezone offset is required") | Rejected at helper, model, and API levels | **PASS** |
| **TC-TIME-006** | Invalid unparseable timestamp strings | Bad strings ("not-a-timestamp", "2026-99-99") | Helper & API parse | Raises `ValueError`, API returns 500 | Bad strings rejected | **PASS** |
| **TC-TIME-007** | Invalid non-string timestamp types | Integer timestamp input `123456` | Parse helper call | Raises `ValueError` ("Expected str or datetime") | Non-string rejected | **PASS** |
| **TC-TIME-008** | Future timestamp within 5m tolerance | Timestamp UTC + 3 minutes | Model & API validation | Accepted, returns `200 OK` | Tolerated drift accepted | **PASS** |
| **TC-TIME-009** | Future timestamp beyond 5m tolerance | Timestamp UTC + 6 minutes | Model & API validation | Raises `ValidationError`, API returns 400 | Excessive drift rejected with 400 | **PASS** |
| **TC-TIME-010** | Stale readings flag (>24h) | Readings 26 hours in past | `GET /api/tank/summary` | `200 OK`, `is_stale: true`, readings preserved | `200 OK`, history preserved with stale tag | **PASS** |
| **TC-TIME-011** | Fresh readings flag ($\le$ 24h) | Readings 15 minutes in past | `GET /api/tank/summary` | `200 OK`, `is_stale: false` | `200 OK`, flagged live | **PASS** |
| **TC-TIME-012** | Monotonic ordering guarantee | Unsorted readings input | `GET /api/tank/summary` | Ascending chronological order returned | Output strictly sorted ascending | **PASS** |
| **TC-TIME-013** | Device status future and stale check | Future & stale device mocks | `GET /device/{id}/status` | Future -> 400, Stale -> 200 `status: "stale"` | Status codes 400 and 200 verified | **PASS** |
| **TC-TIME-014** | Reference time naive rejection | `AQUASENSE_REFERENCE_TIME` naive | `get_current_utc_time()` | Raises `ValueError` ("Timezone offset is required") | Naive env var rejected | **PASS** |
| **TC-TIME-015** | Reference time aware freezes clock | `AQUASENSE_REFERENCE_TIME` aware | `get_current_utc_time()` | Clock frozen at exact UTC equivalent | Deterministic clock freeze verified | **PASS** |
| **TC-TIME-016** | Actual repository JSON file (frozen) | Real `data/mock_data.json` with reference time | `GET /api/tank/summary` & `GET /device/{id}/status` | Current: 55%, Min: 18%, Max: 78%, 8 readings | Assignment telemetry specs verified | **PASS** |
| **TC-TIME-017** | Actual repository JSON file (wall-clock) | Real `data/mock_data.json` without env var | `GET /api/tank/summary` | `current_level: 55.0`, `is_stale: true` (>24h old) | Stale tag verified under wall-clock | **PASS** |

---

## 6. Category 5: Deterministic Mocked Responses (`tests/test_mocked_api_responses.py`)

| Test ID | Test Description | Preconditions | Input / Scenario | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-MOCK-001** | Nominal multi-reading stream | Deterministic mock (3 readings) | `GET /api/tank/summary` | `200 OK`, `current_level: 60.0`, `is_stale: false` | `200 OK`, live metrics verified | **PASS** |
| **TC-MOCK-002** | Stale telemetry mock (>48h) | Mock readings 48 hours ago | `GET /api/tank/summary` | `200 OK`, `is_stale: true`, historical metrics intact | `200 OK`, stale status verified | **PASS** |
| **TC-MOCK-003** | Malformed data source (not a list) | Mock `tank_readings` as string | `GET /api/tank/summary` | `500 Internal Server Error`<br>`detail: "Mock data has no tank readings"` | `500 Internal Server Error`, exact message | **PASS** |
| **TC-MOCK-004** | Corrupted reading items (non-dict) | Mock `tank_readings` has integers | `GET /api/tank/summary` | `500 Internal Server Error`<br>`detail: "Malformed tank reading"` | `500 Internal Server Error`, exact message | **PASS** |
| **TC-MOCK-005** | Offline hardware simulation | Mock device `online: false` | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `503 Service Unavailable`<br>`{"message": "Device is offline", "device_id": "tank-001"}` | `503 Service Unavailable`, exact detail | **PASS** |
| **TC-MOCK-006** | Stale hardware simulation | Mock device seen 36h ago | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `200 OK`, `is_stale: true`, `status: "stale"` | `200 OK`, hardware staleness flagged | **PASS** |
| **TC-MOCK-007** | Auth failure rejection | Missing & corrupted token | `GET /device/tank-001/status` | `401 Unauthorized` for both missing and bad token | `401 Unauthorized` verified | **PASS** |
| **TC-MOCK-008** | Future hardware clock drift (15m) | Mock device 15m in future | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `400 Bad Request` ("future" in detail) | `400 Bad Request`, drift rejected | **PASS** |
| **TC-MOCK-009** | Missing `online` field | Mock device record omits `online` | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `500 Internal Server Error`<br>`detail: "Device record is malformed"` | `500 Internal Server Error`, malformed caught | **PASS** |
| **TC-MOCK-010** | Missing `last_seen` field | Mock device record omits `last_seen` | `GET /device/tank-001/status`<br>`Bearer aquasense-demo-token` | `500 Internal Server Error`<br>`detail: "Device record is malformed"` | `500 Internal Server Error`, malformed caught | **PASS** |
| **TC-MOCK-011** | End-to-end async HTTPX client | ASGI in-memory transport | Async client calls `/health`, `/login`, `/api/tank/summary`, `/device/status` | All endpoints return HTTP 200 with valid JSON | Async client flow verified | **PASS** |
| **TC-MOCK-012** | API root metadata endpoint | Server running | `GET /api` | `200 OK`, `status: "running"`, `docs: "/docs"` | `200 OK`, metadata verified | **PASS** |
| **TC-MOCK-013** | File read error in data loader | Disk I/O error mocked (`OSError`) | `load_data()` call | `500 Internal Server Error`<br>`detail: "Mock data is unavailable or malformed"` | `500 Internal Server Error`, I/O handled | **PASS** |
| **TC-MOCK-014** | Non-dictionary JSON root | JSON payload mocked as list | `load_data()` call | `500 Internal Server Error`<br>`detail: "Mock data must be a JSON object"` | `500 Internal Server Error`, non-dict caught | **PASS** |
| **TC-MOCK-015** | Missing devices list in payload | JSON payload omits `"devices"` list | `get_device("tank-001")` call | `500 Internal Server Error`<br>`detail: "Mock data has no valid devices list"` | `500 Internal Server Error`, missing list caught | **PASS** |
| **TC-MOCK-016** | Unexpected data error handling | `tank_readings()` raises `RuntimeError` | `GET /api/tank/summary` | `500 Internal Server Error`<br>`detail: "Mock data contains an invalid tank reading"` | `500 Internal Server Error`, runtime error handled | **PASS** |
| **TC-MOCK-017** | Path resolver fallback branches | `primary.exists()` mocked as False | `_resolve_data_file()`, `_resolve_frontend_dir()` | Fallback to `cwd` and fallback defaults | Path resolvers verified | **PASS** |

---

## 7. Category 6: Frontend Mathematical & Security Verification (`tests/test_frontend_dashboard_logic.py`)

| Test ID | Test Description | Preconditions | Input / Algorithm | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-FE-001** | Alert boundary 0.0% | Unit test | `evaluateAlertThreshold(0.0)` | `true` (Active alert triggered) | `true` | **PASS** |
| **TC-FE-002** | Alert boundary 0.0001% | Unit test | `evaluateAlertThreshold(0.0001)` | `true` (Active alert triggered) | `true` | **PASS** |
| **TC-FE-003** | Alert boundary 10.5% | Unit test | `evaluateAlertThreshold(10.5)` | `true` (Active alert triggered) | `true` | **PASS** |
| **TC-FE-004** | Alert boundary 19.9% | Unit test | `evaluateAlertThreshold(19.9)` | `true` (Active alert triggered) | `true` | **PASS** |
| **TC-FE-005** | Alert boundary 19.999% | Unit test | `evaluateAlertThreshold(19.999)` | `true` (Active alert triggered) | `true` | **PASS** |
| **TC-FE-006** | Alert boundary 20.0% (exact floor) | Unit test | `evaluateAlertThreshold(20.0)` | `false` (Nominal capacity) | `false` | **PASS** |
| **TC-FE-007** | Alert boundary 20.001% | Unit test | `evaluateAlertThreshold(20.001)` | `false` (Nominal capacity) | `false` | **PASS** |
| **TC-FE-008** | Alert boundary 20.1% | Unit test | `evaluateAlertThreshold(20.1)` | `false` (Nominal capacity) | `false` | **PASS** |
| **TC-FE-009** | Alert boundary 55.0% | Unit test | `evaluateAlertThreshold(55.0)` | `false` (Nominal capacity) | `false` | **PASS** |
| **TC-FE-010** | Alert boundary 100.0% | Unit test | `evaluateAlertThreshold(100.0)` | `false` (Nominal capacity) | `false` | **PASS** |
| **TC-FE-011** | Alert invalid type rejection | Unit test | `evaluateAlertThreshold("abc")`, `evaluateAlertThreshold(True)` | Raises `TypeError` | `TypeError` raised | **PASS** |
| **TC-FE-012** | Assignment dataset metrics verification | Real mock JSON | Current: 55%, Min: 18%, Max: 78% | `active_alert: false`, historical low events = 1 | Current 55%, Min 18%, Max 78%, Low 18% | **PASS** |
| **TC-FE-013** | Time-proportional chart X-coordinates | 3 readings (06:00, 06:30, 20:00) | `calculateChartPoints(readings)` | Point 0: 46.0px, Point 1: 70.79px, Point 2: 740.0px | Proportional spacing verified (70.79px vs index midpoint 393px) | **PASS** |
| **TC-FE-014** | Single reading chart centering | 1 reading input | `calculateChartPoints([reading])` | Point centered at `393.0px` | Centered at 393.0px | **PASS** |
| **TC-FE-015** | Empty readings chart handling | Empty list `[]` | `calculateChartPoints([])` | Empty list `[]` without error | Empty list returned cleanly | **PASS** |
| **TC-FE-016** | Frontend schema validation rules | Corrupted payload inputs | Min > Max, level > 100, naive ts | Validator raises `ValueError` | Out-of-range & naive ts rejected | **PASS** |
| **TC-FE-017** | Static code audit: Zero `innerHTML` | `dashboard.js` AST & text scan | Check for dynamic `.innerHTML` | 0 occurrences in executable code | 0 dynamic innerHTML assignments | **PASS** |
| **TC-FE-018** | Static HTML & CSS semantic hooks audit | `index.html` & `styles.css` scan | Check required IDs and classes | All 11 IDs and 8 CSS classes present | All required DOM hooks present | **PASS** |
| **TC-FE-019** | Full tank summary contract satisfaction | FastAPI client call | `GET /api/tank/summary` | Validates against frontend schema | Schema contract satisfied | **PASS** |
| **TC-FE-020** | Full device status contract & auth | FastAPI client call | `POST /login` + `GET /device/status` | Validates against frontend schema | Schema contract satisfied | **PASS** |
