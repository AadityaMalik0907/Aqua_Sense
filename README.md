# AquaSense

> **Smart Water Tank Monitoring Dashboard**

AquaSense is an automated fluid telemetry microservice and operator dashboard developed for the Nivoryx Systems technical assignment. It tracks reservoir capacity levels, detects safety threshold breaches (<20%), and monitors IoT device connectivity and telemetry freshness. Built with a FastAPI backend and a responsive vanilla JavaScript web dashboard, it provides clear visibility into reservoir metrics and historical consumption trends.

---

## Live Demo and Repository

- **GitHub Repository**: [https://github.com/AadityaMalik0907/Aqua_Sense](https://github.com/AadityaMalik0907/Aqua_Sense)
- **Local Application URL**: `http://127.0.0.1:8000/` (Swagger API docs at `http://127.0.0.1:8000/docs`)
- **Deployment Status**: Configured for serverless hosting on Vercel (`vercel.json` and `api/index.py`).
- **Telemetry Mode**: The application currently runs on simulated JSON telemetry (`data/mock_data.json`) rather than live sensor hardware.

---

## Dashboard Preview

<!-- Place dashboard screenshot in frontend/ or docs/ if capturing preview media -->
> **Dashboard Preview**  
> _AquaSense Oceanic Glassmorphism Dashboard: dual level visualizers, animated column, real-time metrics, SVG telemetry trend chart, and safety status indicators._

---

## Key Features

- **Tank Level Monitoring**: Visual display with dual indicators: a calibrated circular arc gauge (0%–100%) and an animated fluid cylinder.
- **Current, Minimum, and Maximum Levels**: Computes and displays current volume alongside daily minimum and maximum readings.
- **Low-Level Threshold Alert (< 20%)**: Automatic active warning banner triggered whenever the current level drops below 20%.
- **Historical Low-Level Events**: Isolates past threshold breaches into an audit log without triggering a false active alarm when current levels recover.
- **Telemetry Freshness & Stale Detection**: Timezone-aware UTC timestamp normalization flags data older than 24 hours as stale, preventing outdated data from masquerading as live.
- **Bearer-Token Authentication**: Secure access to IoT device telemetry via Bearer token authentication (`POST /login`).
- **Device Status & Pump State**: Hardware connectivity reporting via `GET /device/{id}/status`, including online/offline/stale state, level percent, and pump status (`"on"`/`"off"`).
- **Automated Tests**: 92 automated tests with 100% backend statement coverage verifying endpoints, schemas, and edge conditions.

---

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pydantic v2
- **Testing**: pytest (9.2.0), pytest-cov (7.1.0), HTTPX (0.28.1), FastAPI TestClient, unittest.mock
- **Frontend**: Semantic HTML5, Glassmorphism CSS3, Vanilla JavaScript (ES6+), SVG
- **Configuration & Storage**: JSON (`data/mock_data.json`), Vercel Serverless (`vercel.json`, `api/index.py`)

---

## Project Structure

```text
AquaSense/
├── api/
│   └── index.py                 # Vercel serverless ASGI entry point
├── backend/
│   └── app/
│       ├── auth.py              # Bearer authentication logic
│       ├── data.py              # Mock data loader and device lookup
│       ├── main.py              # FastAPI application, routing, and static mounts
│       ├── models.py            # Pydantic v2 request/response schemas
│       └── time_utils.py        # UTC normalization, freshness, and clock-drift validation
├── data/
│   └── mock_data.json           # 8-reading assignment dataset and IoT device records
├── docs/
│   ├── ai_usage.md              # AI collaboration record, prompts, and corrections
│   ├── mobile_testing.md        # Mobile network resiliency and Wi-Fi drop specification
│   └── test-cases.md            # Register of all 92 automated test cases
├── frontend/
│   ├── css/styles.css           # Oceanic Glassmorphism styling and responsive layout
│   ├── js/dashboard.js          # API polling, linear SVG chart math, and safe DOM binding
│   ├── index.html               # Main dashboard web console
│   └── test-dashboard.html      # In-browser test harness for frontend logic
├── tests/                       # 92 automated unit, integration, and contract tests
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Python dependencies
└── vercel.json                  # Edge CDN and serverless route rules
```

---

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Windows PowerShell (or bash on Linux/macOS)
- Git

### Installation & Setup (Windows PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/AadityaMalik0907/Aqua_Sense.git
cd Aqua_Sense

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the FastAPI server
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### URLs
- **Dashboard UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Specification**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **In-Browser Test Runner**: [http://127.0.0.1:8000/test-dashboard.html](http://127.0.0.1:8000/test-dashboard.html)

---

## API Documentation

### 1. `POST /login`
Authenticates credentials and returns a Bearer access token.

- **Authentication**: None
- **Request Body**:
  ```json
  { "username": "demo", "password": "aqua123" }
  ```
- **Response (`200 OK`)**:
  ```json
  { "access_token": "aquasense-demo-token", "token_type": "bearer" }
  ```
- **Errors**: Invalid credentials return `401 Unauthorized` (`{"detail": "Invalid credentials"}`). Missing fields return `422 Unprocessable Entity`.

---

### 2. `GET /device/{id}/status`
Inspects physical IoT hardware connectivity, pump state, fluid level, and last seen timestamp.

- **Authentication**: `Bearer <access_token>`
- **Sample Request**: `GET /device/tank-001/status`
- **Response (`200 OK`)**:
  ```json
  {
    "id": "tank-001",
    "online": true,
    "last_seen": "2026-11-02T14:30:00Z",
    "is_stale": true,
    "status": "stale",
    "level_percent": 55.0,
    "pump_state": "off"
  }
  ```
- **Errors**:
  - Missing or invalid token: `401 Unauthorized` (`{"detail": "Not authenticated"}`)
  - Device offline: `503 Service Unavailable` (`{"detail": {"message": "Device is offline", "device_id": "device-offline"}}`)
  - Device not found: `404 Not Found` (`{"detail": "Device not found"}`)

---

### 3. `GET /api/tank/summary`
Returns aggregated tank telemetry, chronological readings, min/max statistics, and active alert state.

- **Authentication**: None
- **Response (`200 OK`)**:
  ```json
  {
    "current_level": 55.0,
    "minimum_level": 18.0,
    "maximum_level": 78.0,
    "active_alert": false,
    "historical_low_events": [
      { "timestamp": "2026-11-02T10:30:00Z", "level": 18.0 }
    ],
    "readings": [
      { "timestamp": "2026-11-02T00:30:00Z", "level": 78.0 },
      { "timestamp": "2026-11-02T02:30:00Z", "level": 64.0 },
      { "timestamp": "2026-11-02T04:30:00Z", "level": 51.0 },
      { "timestamp": "2026-11-02T06:30:00Z", "level": 37.0 },
      { "timestamp": "2026-11-02T08:30:00Z", "level": 24.0 },
      { "timestamp": "2026-11-02T10:30:00Z", "level": 18.0 },
      { "timestamp": "2026-11-02T12:30:00Z", "level": 42.0 },
      { "timestamp": "2026-11-02T14:30:00Z", "level": 55.0 }
    ],
    "is_stale": true,
    "latest_reading_timestamp": "2026-11-02T14:30:00Z"
  }
  ```

---

## Assignment Requirements Mapping

| Assignment Requirement | Implementation Location | Verification Test | Expected Dataset Result |
| :--- | :--- | :--- | :--- |
| **Part A: Current Tank Level** | `backend/app/main.py` (`/api/tank/summary`), `frontend/js/dashboard.js` | `test_tank_levels.py`, `test_frontend_dashboard_logic.py` | **55%** (recorded at 20:00 IST / 14:30 UTC) |
| **Part A: Minimum Level** | `backend/app/main.py` (`minimum_level`) | `test_tank_levels.py` | **18%** (recorded at 16:00 IST / 10:30 UTC) |
| **Part A: Maximum Level** | `backend/app/main.py` (`maximum_level`) | `test_tank_levels.py` | **78%** (recorded at 06:00 IST / 00:30 UTC) |
| **Part B: Active Low Alert (<20%)** | `backend/app/main.py` (`active_alert = current < 20`) | `test_tank_levels.py`, `test_frontend_dashboard_logic.py` | **`false`** (current 55% $\ge$ 20%) |
| **Part B: Historical Low Events** | `backend/app/main.py` (`historical_low_events`) | `test_tank_levels.py` | **1 event** (18% at 16:00 IST) in audit log |

---

## Testing

Run the automated test suite from the repository root:

```powershell
# Run all 92 automated tests
.\.venv\Scripts\python.exe -m pytest -v

# Run with test coverage analysis
.\.venv\Scripts\python.exe -m pytest --cov=backend/app --cov-report=term-missing
```

### Verified Test Results
- **Collected & Passed**: **92 / 92 tests (100% pass rate)** in 1.53s.
- **Statement Coverage**: **100%** (213 / 213 statements across `backend/app`).
- **Test Modules**:
  - `tests/test_login.py`: Authentication, credential rejection, and payload validation (11 tests).
  - `tests/test_device_status.py`: Bearer token enforcement, offline 503 handling, schema contracts (14 tests).
  - `tests/test_tank_levels.py`: Boundary conditions (0%, 19.9%, 20%, 20.1%, 100%) and malformed inputs (13 tests).
  - `tests/test_timestamps_and_freshness.py`: UTC normalization, 300s clock drift limit, 24h staleness (17 tests).
  - `tests/test_mocked_api_responses.py`: Deterministic mock tests for device states and error handling (17 tests).
  - `tests/test_frontend_dashboard_logic.py`: Proportional chart coordinates, DOM safety, alert logic (20 tests).

Full test cases and execution records are documented in [`docs/test-cases.md`](docs/test-cases.md).

---

## Mobile Network Behaviour

When client Wi-Fi is lost during active operations, network listeners immediately flag the disconnection. Instead of resetting metrics or clearing the view, the interface retains last-known data, presents an offline banner, and enters an exponential backoff retry loop (1s to 30s ceiling). Upon reconnection, the client reconciles state via `GET /device/{id}/status` and `GET /api/tank/summary`. Write commands use idempotent tokens (UUIDv4) to prevent duplicate execution.

_Note_: The current repository provides a responsive web dashboard; native mobile background listeners and hardware valve controls reflect planned mobile client architecture. See [`docs/mobile_testing.md`](docs/mobile_testing.md) for the complete specification.

---

## AI Usage

- **Tool Used**: Google Antigravity coding assistant (powered by Claude 3.7 Sonnet and Gemini 3.8 Flash).
- **Prompt 1 (Backend Implementation)**:
  > _"Inspect the existing AquaSense repository and implement the backend requirements of the Nivoryx assignment. First, review the existing architecture, API endpoints, data models, mock data, and tests before making changes._
  > 
  > _Ensure that:_
  > _- Tank readings are validated and current, minimum, and maximum levels are calculated correctly._
  > _- Low-level alerts trigger only when the latest reading is below 20%, with historical low-level events tracked separately._
  > _- POST /login provides token-based authentication._
  > _- GET /device/{id}/status returns level_percent, pump_state ("on" or "off"), and last_seen._
  > _- Invalid tokens, unknown devices, offline devices, stale timestamps, malformed data, and missing fields are handled correctly._
  > _- Empty telemetry is distinguished from an actual 0% tank level._
  > 
  > _Preserve existing functionality and API compatibility. Add or update automated tests, including at least four tests using mocked API responses. Run the test suite, fix implementation-related failures, and report the actual results. Do not fabricate data, introduce unnecessary changes, or claim unverified functionality."_
- **Prompt 2 (Frontend Dashboard)**:
  > _"Inspect the existing AquaSense frontend and implement the dashboard requirements of the Nivoryx assignment. Ensure the dashboard accurately displays the current tank level, minimum level, maximum level, last reading timestamp, and historical readings using validated backend data._
  > 
  > _Implement correct alert handling: readings below 20% trigger an active alert only when they are the latest reading. Historical low-level events must be displayed separately and must not be mistaken for active alerts._
  > 
  > _Ensure the dashboard handles stale telemetry, offline devices, API failures, invalid responses, empty readings, and network interruptions without displaying fabricated or misleading values. Preserve the existing design and responsive behaviour while improving reliability and usability._
  > 
  > _Verify that the supplied mock data produces a current level of 55%, minimum of 18%, maximum of 78%, and no active alert. Add or update relevant automated tests, run the available test suite, and report actual results and any remaining issues. Avoid unnecessary redesigns or changes to working functionality."_
- **Genuine Mistake & Correction**: The AI initially used index-based spacing (`index / (N - 1)`) for the SVG chart X-axis, distorting irregular timestamp intervals, and inserted dynamic data via `innerHTML`. This was caught during code inspection and corrected by implementing linear epoch millisecond geometry `left + ((t - min_t) / (max_t - min_t)) * plotWidth` and replacing `innerHTML` with safe DOM methods (`document.createElement()`, `textContent`).

A detailed chronology and prompt history is recorded in [`docs/ai_usage.md`](docs/ai_usage.md).

---

## Limitations

- **Simulated JSON Telemetry**: Sensor readings are sourced from a static file (`data/mock_data.json`). In production, readings would be ingested via MQTT/CoAP into a time-series database.
- **Simulated Hardware State**: Device connectivity and pump states reflect mock records rather than live PLC or microcontroller telemetry.
- **No Physical Hardware Integration**: The microservice does not currently interface with physical Modbus, RS485, or LoRaWAN sensors.
- **Evaluation Credential Store**: Authentication uses a static evaluation credential pair (`demo` / `aqua123`). Production deployments would require OAuth2/OIDC with hashed passwords and signed JWT expiry.
- **Wall-Clock Staleness**: Because the assignment dataset is dated November 2, 2026, real wall-clock execution marks data as stale (`is_stale: true`). Deterministic fresh testing is supported using the `AQUASENSE_REFERENCE_TIME` environment variable.
