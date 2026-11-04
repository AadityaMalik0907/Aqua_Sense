# AquaSense | Intelligent Tank Telemetry & Fluid Monitoring Platform

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Pytest-92%20Passed-brightgreen.svg)](docs/test-cases.md)
[![Coverage](https://img.shields.io/badge/Coverage-100%25-brightgreen.svg)](docs/PHASE_3_REPORT.md)

AquaSense is an industrial and municipal fluid telemetry microservice and control dashboard developed for **Nivoryx Systems Private Limited**. It couples a high-performance **FastAPI** backend with a responsive, glassmorphic **Oceanic Web Dashboard** to deliver continuous capacity tracking, threshold breach detection, chronological telemetry graphing, and hardware connectivity monitoring.

**GitHub Repository**: [https://github.com/AadityaMalik0907/Aqua_Sense](https://github.com/AadityaMalik0907/Aqua_Sense)

---

## Table of Contents

1. [Assignment Objective](#1-assignment-objective)
2. [Project Overview](#2-project-overview)
3. [Key Features](#3-key-features)
4. [Technology Stack](#4-technology-stack)
5. [System Architecture](#5-system-architecture)
6. [Folder Structure](#6-folder-structure)
7. [Prerequisites](#7-prerequisites)
8. [Windows Installation & Setup](#8-windows-installation--setup)
9. [Running the Application](#9-running-the-application)
10. [Accessing the Dashboard & API Docs](#10-accessing-the-dashboard--api-docs)
11. [API Endpoint Documentation](#11-api-endpoint-documentation)
12. [Sample Requests & Responses](#12-sample-requests--responses)
13. [Expected Tank Telemetry Metrics](#13-expected-tank-telemetry-metrics)
14. [Low-Level Safety Threshold Logic](#14-low-level-safety-threshold-logic)
15. [Device Status Response Schema Contract](#15-device-status-response-schema-contract)
16. [Automated Testing & Coverage](#16-automated-testing--coverage)
17. [Deploying to Vercel](#17-deploying-to-vercel)
18. [Assumptions and Limitations](#18-assumptions-and-limitations)

---

## 1. Assignment Objective

The goal of this assignment is to construct a verified, production-grade fluid monitoring solution satisfying:
- **Part A (Tank Level Dashboard)**: Display the current reservoir level, today's minimum and maximum levels, and last sample timestamp based on the provided 8-reading dataset.
- **Part B (Safety Threshold Alert)**: Trigger an active visual alert strictly when the current tank level falls below **20%**, while isolating historical low-level events to an audit log.
- **Part C (Data Freshness & Staleness)**: Detect when sensor telemetry is older than 24 hours (`is_stale: true`) and adjust the dashboard UI accordingly without showing a misleading live state.
- **Part D (Device Connectivity Separation)**: Clearly distinguish between HTTP API reachability (topbar pill) and physical IoT device reachability (tank card tag), preventing false assumptions when local networks fail.
- **Part E (Timestamp & Telemetry Accuracy)**: Enforce timezone-aware UTC normalization, reject future clock drift beyond a 5-minute tolerance, and plot timeline points on an SVG chart proportionally based on elapsed milliseconds.

---

## 2. Project Overview

Managing municipal reservoirs and industrial storage requires uninterrupted visibility into capacity trends. AquaSense provides an end-to-end telemetry pipeline:
1. **Field Telemetry Ingestion**: Ingests sensor readings containing ISO 8601 timestamps and percentage capacities ($[0.0, 100.0]$).
2. **RESTful Microservice**: Validates data schemas, enforces Bearer token authentication, normalizes timezone offsets to UTC, and detects offline or stale hardware.
3. **Glassmorphic Control Console**: Delivers real-time operator feedback through dual liquid level visualizers (radial gauge + vertical wave cylinder), safety alert banners, and interactive SVG charts with hover tooltips.

---

## 3. Key Features

- **Oceanic Glassmorphism Interface**: High-aesthetic UI featuring backdrop blurs, ambient radial glows, and liquid wave keyframe animations.
- **Dual Visualizer Engine**:
  - *Calibrated Radial Dial*: Displays capacity percentage ($0\%$ to $100\%$) with color-coded arc tracks.
  - *Animated Liquid Column*: Acrylic cylinder with oscillating SVG wave tops, floating bubbles, and a glowing 20% critical threshold marker.
- **Accurate Alert Separation**: Current level $55\% \ge 20\%$ shows *"All systems nominal"* ($0$ active alerts). The historical $18\%$ event at 16:00 is isolated to the Audit Log.
- **Time-Proportional SVG Chart**: X-axis coordinates are calculated using linear millisecond elapsed math:
  $$\text{x} = \text{left} + \left(\frac{t - \min(t)}{\max(t) - \min(t)}\right) \times \text{plotWidth}$$
  Irregular sensor intervals (e.g., 06:00, 06:30, 20:00) render with truthful spacing rather than artificial index-based distribution.
- **Separated Connectivity Monitoring**:
  - *API Status*: Indicates client-to-FastAPI HTTP connectivity (`API: Connected`, `API: Updating`, `API: Offline`).
  - *Device Status*: Queries `GET /device/tank-001/status` using Bearer tokens to inspect actual hardware state (`Online`, `Offline`, `Stale`, `Auth Required`).
- **Telemetry Freshness & Cache Retention**: When data is stale (>24h), the live green beacon switches to amber, status chips indicate historical data, and warning notices explain telemetry age. If network drops, previously loaded valid metrics remain visible on screen with a cached warning banner.
- **Security Hardening**: Zero `innerHTML` assignments in dynamic JavaScript rendering, preventing DOM injection attacks.
- **Theme Switcher**: Instant toggle between *Oceanic Midnight Glass* (dark) and *Pristine Marine Daylight* (light) modes.

---

## 4. Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) `0.115+`
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/) `0.30+`
- **Data Validation & Modeling**: [Pydantic v2](https://docs.pydantic.dev/)
- **Testing Engine**: [Pytest](https://docs.pytest.org/) `9.2.0`, [pytest-cov](https://pytest-cov.readthedocs.io/) `7.1.0`, FastAPI `TestClient`, [HTTPX](https://www.python-httpx.org/) `0.28.1`, `unittest.mock`
- **Frontend Stack**: Pure Semantic HTML5, Glassmorphic CSS3 (CSS Variables, Flexbox/Grid), Vanilla ES6+ JavaScript, SVG NS
- **Runtime Environment**: Python `3.10+` (tested and verified on Python `3.15.2` on Windows 11)

---

## 5. System Architecture

```mermaid
flowchart TD
    subgraph Browser ["Frontend Dashboard Client"]
        UI["Oceanic Glassmorphism UI\n(index.html / styles.css)"]
        Engine["Telemetry Engine (dashboard.js)\n• AbortController\n• Time-Proportional Math\n• Schema Validators\n• Safe DOM Methods"]
    end

    subgraph Backend ["FastAPI Application (backend/app/)"]
        Auth["auth.py\n• Bearer Scheme\n• Credential Validation"]
        TimeUtil["time_utils.py\n• UTC Normalization\n• Clock Drift Check (5m)\n• Staleness (24h)"]
        Router["main.py\n• POST /login\n• GET /api/tank/summary\n• GET /device/{id}/status\n• Static Mounts"]
        Models["models.py\nPydantic v2 Models\n(TankReading, DeviceStatus)"]
        DataLayer["data.py\nJSON Loader & Device Lookup"]
    end

    subgraph Storage ["Persistent Mock Store"]
        JSON[("data/mock_data.json\n• 8 Assignment Readings\n• IoT Device Registry")]
    end

    UI --> Engine
    Engine -- "HTTP GET /api/tank/summary" --> Router
    Engine -- "HTTP POST /login" --> Router
    Engine -- "HTTP GET /device/tank-001/status (Bearer)" --> Router
    Router --> Auth
    Router --> TimeUtil
    Router --> Models
    Router --> DataLayer
    DataLayer --> JSON
```

---

## 6. Folder Structure

```text
AquaSense/
├── backend/
│   └── app/
│       ├── __init__.py          # Package initializer
│       ├── auth.py              # Mock Bearer token authentication logic
│       ├── data.py              # Mock data loader and integrity validator
│       ├── main.py              # FastAPI endpoints, routers, and static file mounting
│       ├── models.py            # Pydantic v2 data models and validators
│       └── time_utils.py        # Timezone normalization, future check, and freshness
├── data/
│   └── mock_data.json           # 8 assignment readings (2026-11-02) and IoT devices
├── docs/
│   ├── ai_usage.md              # AI collaboration log and assignment-ready note
│   ├── mobile_testing.md        # Mobile Wi-Fi drop resiliency and recovery spec
│   ├── PHASE_1_REPORT.md        # Phase 1 backend hardening report
│   ├── PHASE_2_REPORT.md        # Phase 2 frontend correctness report
│   ├── PHASE_3_REPORT.md        # Phase 3 comprehensive testing report
│   └── test-cases.md            # Detailed register of all 92 automated test cases
├── frontend/
│   ├── css/
│   │   └── styles.css           # Oceanic Glassmorphism styling and themes
│   ├── js/
│   │   └── dashboard.js         # Telemetry synchronization, chart, and validation logic
│   ├── index.html               # Main dashboard web console
│   └── test-dashboard.html      # Interactive in-browser verification test runner
├── tests/
│   ├── test_device_status.py    # Device telemetry, token auth, and schema tests
│   ├── test_frontend_dashboard_logic.py # Alert thresholds, chart math, and security tests
│   ├── test_login.py            # Authentication, invalid password, and malformed payload tests
│   ├── test_mocked_api_responses.py # Deterministic mock tests (stale, offline, error branches)
│   ├── test_tank_levels.py      # Tank level boundary and Pydantic validation tests
│   └── test_timestamps_and_freshness.py # UTC normalization, clock drift, and ordering tests
├── .gitignore                   # Git exclusion rules (venv, caches, logs)
├── pytest.ini                   # Pytest configuration and warning filters
├── README.md                    # Project documentation (this file)
└── requirements.txt             # Python production and testing dependencies
```

---

## 7. Prerequisites

- **Operating System**: Windows 10/11, macOS, or Linux.
- **Python**: Version `3.10` or higher (`python --version`).
- **PowerShell**: Version `5.1` or PowerShell `7+` (on Windows).
- **Git**: Installed and configured (`git --version`).

---

## 8. Windows Installation & Setup

Execute the following commands in **Windows PowerShell**:

### 1. Clone the Repository
```powershell
git clone https://github.com/AadityaMalik0907/Aqua_Sense.git
cd Aqua_Sense
```

### 2. Create a Virtual Environment
```powershell
python -m venv .venv
```

### 3. Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

> **PowerShell ExecutionPolicy Note**: If you encounter a script execution restriction, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> Then run `.\.venv\Scripts\Activate.ps1` again.

### 4. Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. Running the Application

Launch the Uvicorn ASGI server with hot-reload enabled:

```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

To run using Python directly:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## 10. Accessing the Dashboard & API Docs

| Interface | URL | Description |
| :--- | :--- | :--- |
| **AquaSense Control Dashboard** | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | Live reservoir monitoring, gauges, visualizers, and audit log |
| **Interactive OpenAPI (Swagger)** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive API playground with try-it-out functionality |
| **Alternative ReDoc Docs** | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | Clean, searchable OpenAPI technical specification |
| **In-Browser Test Harness** | [http://127.0.0.1:8000/test-dashboard.html](http://127.0.0.1:8000/test-dashboard.html) | Real-time frontend mathematical engine test runner |

---

## 11. API Endpoint Documentation

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | No | Serves the Oceanic dashboard (`frontend/index.html`) |
| `GET` | `/health` | No | Lightweight process health check (`{"status": "ok"}`) |
| `GET` | `/api` | No | Service metadata, status, and link to documentation |
| `POST` | `/login` | No | Validates credentials and returns a Bearer access token |
| `GET` | `/api/tank/summary` | No | Returns current level, min/max, active alert flag, and chronological readings |
| `GET` | `/device/{device_id}/status` | **Bearer Token** | Returns hardware state, `level_percent`, `pump_state`, and `last_seen` timestamp |

---

## 12. Sample Requests & Responses

### 1. `POST /login` (User Authentication)
- **Request**:
```bash
curl -X POST "http://127.0.0.1:8000/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "demo", "password": "aqua123"}'
```
- **Response (`200 OK`)**:
```json
{
  "access_token": "aquasense-demo-token",
  "token_type": "bearer"
}
```

---

### 2. `GET /api/tank/summary` (Tank Telemetry Summary)
- **Request**:
```bash
curl -X GET "http://127.0.0.1:8000/api/tank/summary" -H "Accept: application/json"
```
- **Response (`200 OK`)**:
```json
{
  "current_level": 55.0,
  "minimum_level": 18.0,
  "maximum_level": 78.0,
  "active_alert": false,
  "historical_low_events": [
    {
      "timestamp": "2026-11-02T16:00:00+05:30",
      "level": 18.0
    }
  ],
  "readings": [
    { "timestamp": "2026-11-02T06:00:00+05:30", "level": 78.0 },
    { "timestamp": "2026-11-02T08:00:00+05:30", "level": 64.0 },
    { "timestamp": "2026-11-02T10:00:00+05:30", "level": 51.0 },
    { "timestamp": "2026-11-02T12:00:00+05:30", "level": 37.0 },
    { "timestamp": "2026-11-02T14:00:00+05:30", "level": 24.0 },
    { "timestamp": "2026-11-02T16:00:00+05:30", "level": 18.0 },
    { "timestamp": "2026-11-02T18:00:00+05:30", "level": 42.0 },
    { "timestamp": "2026-11-02T20:00:00+05:30", "level": 55.0 }
  ],
  "is_stale": true,
  "latest_reading_timestamp": "2026-11-02T20:00:00+05:30"
}
```

---

### 3. `GET /device/tank-001/status` (Authenticated Device Status)
- **Request**:
```bash
curl -X GET "http://127.0.0.1:8000/device/tank-001/status" \
     -H "Authorization: Bearer aquasense-demo-token"
```
- **Response (`200 OK`)**:
```json
{
  "id": "tank-001",
  "online": true,
  "status": "stale",
  "last_seen": "2026-11-02T14:30:00Z",
  "is_stale": true,
  "level_percent": 55.0,
  "pump_state": "off"
}
```

---

### 4. `GET /device/device-offline/status` (Offline Hardware Error)
- **Request**:
```bash
curl -X GET "http://127.0.0.1:8000/device/device-offline/status" \
     -H "Authorization: Bearer aquasense-demo-token"
```
- **Response (`503 Service Unavailable`)**:
```json
{
  "detail": {
    "message": "Device is offline",
    "device_id": "device-offline"
  }
}
```

---

## 13. Expected Tank Telemetry Metrics

For the assignment dataset (`data/mock_data.json`), the expected values are:

| Metric | Expected Value | Explanation |
| :--- | :--- | :--- |
| **Current Level** | **`55%`** | The latest chronological reading (recorded at `20:00:00+05:30`). |
| **Minimum Level** | **`18%`** | The lowest recorded capacity in the cycle (reached at `16:00:00+05:30`). |
| **Maximum Level** | **`78%`** | The peak capacity in the cycle (recorded at `06:00:00+05:30`). |
| **Active Alert** | **`false`** | The current capacity ($55\%$) is safely above the $20\%$ critical threshold. |
| **Historical Events** | **`1 event`** | The single threshold dip at `16:00` ($18\%$) is logged in the audit trail. |
| **Last Sample Timestamp**| **`02 Nov 2026, 20:00`** | Time of the final telemetry ingestion. |

---

## 14. Low-Level Safety Threshold Logic

The safety alert evaluation adheres strictly to the following mathematical condition:

$$\text{Active Alert} = \begin{cases} \text{true} & \text{if } \text{current\_level} < 20.0 \\ \text{false} & \text{if } \text{current\_level} \ge 20.0 \end{cases}$$

### Boundary Conditions Verified:
- **`0.0%`**: Active alert triggered.
- **`19.9%`**: Active alert triggered ($< 20\%$).
- **`20.0%`**: **Nominal** (No active alert; $20.0\% \ge 20\%$).
- **`20.1%`**: Nominal (No active alert).
- **`100.0%`**: Nominal (No active alert).

> **Active vs Historical Distinction**: An active alert reflects **only the current reading**. Historical low-level events ($18\%$ at 16:00) are listed in the Audit Log and marked on the chart (`.low-point`), but do **not** trigger an active emergency state when current levels recover to $55\%$.

---

## 15. Device Status Response Schema Contract

The `GET /device/{id}/status` endpoint guarantees the following strict schema:

| Field | Data Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `id` | `string` | Non-empty | Unique identifier of the field hardware (e.g., `"tank-001"`). |
| `online` | `boolean` | `true` or `false` | Physical connection state. Offline devices return HTTP 503. |
| `status` | `string` | `"online"`, `"stale"` | Human-readable connectivity status. |
| `last_seen` | `string` | ISO 8601 UTC | Validated UTC timestamp (e.g., `"2026-11-02T14:30:00Z"`). |
| `is_stale` | `boolean` | `true` or `false` | `true` if `(now_utc - last_seen) > 86400` seconds (24h). |
| `level_percent`| `float` | $[0.0, 100.0]$ | Live fluid level reported by the device sensor. |
| `pump_state` | `string` | `"on"` or `"off"` | Current mechanical state of the reservoir inlet pump. |

---

## 16. Automated Testing & Coverage

AquaSense features a comprehensive automated test harness consisting of **92 unit, integration, and property-based test cases**.

### Run Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Run Code Coverage Analysis
```powershell
.\.venv\Scripts\python.exe -m pytest --cov=backend --cov-report=term-missing
```

### Coverage Results
- **Statements**: 213
- **Missed**: 0
- **Coverage**: **100%**

```
Name                        Stmts   Miss  Cover   Missing
---------------------------------------------------------
backend\app\__init__.py         0      0   100%
backend\app\auth.py            16      0   100%
backend\app\data.py            43      0   100%
backend\app\main.py            94      0   100%
backend\app\models.py          26      0   100%
backend\app\time_utils.py      34      0   100%
---------------------------------------------------------
TOTAL                         213      0   100%
```

---

## 17. Deploying to Vercel

AquaSense includes zero-configuration deployment support for Vercel:

1. Push your repository to GitHub:
   ```powershell
   git push origin main
   ```
2. Log into [Vercel](https://vercel.com) and click **"Add New" -> "Project"**.
3. Import `AadityaMalik0907/Aqua_Sense`.
4. Leave all build settings at default (Vercel automatically identifies `requirements.txt` and `vercel.json`).
5. Click **"Deploy"**.

### Vercel Routing Configuration:
- `api/index.py`: Serverless ASGI entrypoint bridging Vercel to `backend.app.main:app`.
- `vercel.json`: Directs API requests (`/api/*`, `/health`, `/login`, `/device/*`, `/docs`) to the Python serverless function, while serving static frontend assets (`/`, `/css/*`, `/js/*`) via Vercel Edge CDN.

---

## 18. Assumptions and Limitations

1. **Authentication Mode**: For assignment evaluation, the backend uses a deterministic mock authentication store (`demo` / `aqua123` issuing `aquasense-demo-token`). In production, this would be replaced with OAuth2/OIDC, PBKDF2/Argon2 password hashing, and cryptographically signed JWTs.
2. **Telemetry Ingestion**: Readings are currently loaded from a local JSON store (`data/mock_data.json`). Physical industrial deployments would stream data over MQTT/CoAP into a time-series database (e.g., TimescaleDB or InfluxDB).
3. **Staleness Boundary**: Devices and sensor streams are flagged as stale when more than 24 hours (`86,400` seconds) have elapsed without communication.
4. **Future Timestamp Tolerance**: To accommodate real-world field device clock drift while rejecting fabricated timestamps, readings up to **5 minutes (300 seconds)** in the future are accepted; readings exceeding 5 minutes are rejected with HTTP 400.
5. **Mobile Architecture**: The platform currently provides a web-based dashboard. Mobile integration guidelines are formally specified in [`docs/mobile_testing.md`](docs/mobile_testing.md).
