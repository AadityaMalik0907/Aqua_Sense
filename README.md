# AquaSense | Intelligent Tank Telemetry & Reservoir Monitoring

AquaSense is a modern water telemetry platform designed for industrial, municipal, and residential fluid storage management. It pairs a **FastAPI** backend with a high-performance, glassmorphic **Oceanic Web Dashboard** to deliver real-time reservoir capacity tracking, automated low-level threshold detection, interactive historical trend analysis, and simulated device health monitoring.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Directory Structure](#project-directory-structure)
- [Windows Installation & Setup](#windows-installation--setup)
- [Running the Application](#running-the-application)
- [Deploying to Vercel](#deploying-to-vercel)
- [API Documentation & Endpoints](#api-documentation--endpoints)
- [Sample API Responses](#sample-api-responses)
- [Automated Testing](#automated-testing)
- [Assumptions and Limitations](#assumptions-and-limitations)

---

## Project Overview

Managing water resources requires continuous visibility into storage volume and immediate warning before reserves hit critical thresholds. AquaSense provides an end-to-end telemetry pipeline:
1. **Field Telemetry Stream**: Collects sensor measurements (timestamped percentage levels) and device connectivity states (`online`, `offline`, or `stale`).
2. **REST API Microservice**: Serves sanitized summary data, device connection auditing, and mock Bearer token authentication.
3. **Interactive Control Dashboard**: Delivers visual feedback with dual liquid level visualizers, animated wave motion, threshold alerts, and historical SVG telemetry graphs.

---

## Key Features

- **Cinematic Welcome Experience**: An aquatic splash screen featuring dynamic ambient glow orbs, water wave crests, and a 3-second auto-entry countdown with manual bypass controls.
- **Dual Reservoir Visualizers**:
  - *Precision Arc Gauge*: Circular gradient dial calibrated from 0% to 100%.
  - *Animated Liquid Cylinder*: Acrylic glass column featuring oscillating SVG water waves (`waveMotion`), rising aeration bubbles, and a glowing 20% critical threshold marker.
- **Dynamic Safety Guard**: Automatically highlights when capacity drops below the **20% low threshold floor**, generating actionable incident alerts and logging past violations.
- **Interactive Telemetry Charting**: Vector SVG area chart with multi-stop gradients and hover tooltips showing precise reading timestamps.
- **Dual Color Modes**: Seamless toggle between **Oceanic Midnight Glass** (default deep dark mode) and **Pristine Marine Daylight** mode.
- **Zero-Dependency Frontend**: Pure semantic HTML5, CSS3 (hardware-accelerated animations), and vanilla ES6+ JavaScript.

---

## Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) `0.115+`
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/) `0.30+`
- **Data Validation & Modeling**: [Pydantic v2](https://docs.pydantic.dev/)
- **Testing Engine**: [Pytest](https://docs.pytest.org/) `9.0+` with FastAPI `TestClient` and `HTTPX`
- **Frontend Stack**: Modern HTML5, Glassmorphism CSS3, Vanilla ECMAScript 6, SVG NS
- **Runtime Environment**: Python `3.10+` (tested on Python `3.15.2` on Windows)

---

## Project Directory Structure

```text
AquaSense/
├── backend/
│   └── app/
│       ├── __init__.py          # Package initializer
│       ├── auth.py              # Mock Bearer token authentication logic
│       ├── data.py              # Data loader and integrity validator
│       ├── main.py              # FastAPI application, routing, and static mounts
│       └── models.py            # Pydantic request/response data schemas
├── data/
│   └── mock_data.json           # Mock storage for IoT devices and tank readings
├── docs/
│   ├── ai_usage.md              # AI collaboration, prompt log, and corrections
│   ├── mobile_testing.md        # Mobile Wi-Fi drop & resiliency specification
│   └── test-cases.md            # Detailed record of all 16 executed test cases
├── frontend/
│   ├── css/
│   │   └── styles.css           # Oceanic Glassmorphism styles and animations
│   ├── js/
│   │   └── dashboard.js         # Telemetry synchronization, chart, & welcome logic
│   └── index.html               # Main dashboard HTML template
├── tests/
│   ├── test_device_status.py    # Device connection, auth, and error tests
│   ├── test_login.py            # Login authentication and validation tests
│   └── test_tank_levels.py      # Tank level boundary and Pydantic tests
├── .gitignore                   # Git exclusion rules
├── README.md                    # Project documentation (this file)
└── requirements.txt             # Python dependencies
```

---

## Windows Installation & Setup

Follow these step-by-step instructions to set up the project on a clean Windows machine.

### 1. Prerequisites
Ensure you have Python 3.10 or higher installed and accessible from PowerShell. Verify in terminal:
```powershell
python --version
```

### 2. Clone the Repository
```powershell
git clone https://github.com/your-username/AquaSense.git
cd AquaSense
```

### 3. Create and Activate a Virtual Environment
```powershell
# Create the virtual environment in .venv
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

> **Note for Windows PowerShell Users**: If script execution is restricted, run:
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
> ```
> Then run `.\.venv\Scripts\Activate.ps1` again.

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## Running the Application

### Start the FastAPI Server
With the virtual environment activated, launch Uvicorn:
```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Accessing the System
- **Dashboard Web UI**: Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in any modern browser.
- **Interactive OpenAPI Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc API Specification**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Deploying to Vercel

AquaSense is pre-configured for zero-friction serverless deployment on [Vercel](https://vercel.com):

1. **Push your repository** to GitHub, GitLab, or Bitbucket.
2. In the **Vercel Dashboard**, click **"Add New" -> "Project"** and import the repository.
3. Keep the default settings (Vercel automatically detects Python, installs dependencies from `requirements.txt`, and uses `vercel.json`).
4. Click **"Deploy"**.

### What Vercel Configures Automatically:
- `api/index.py`: Serverless ASGI function entrypoint.
- `vercel.json`: Edge CDN rewrites routing `/api/*`, `/health`, `/login`, `/device/*`, and `/docs` to FastAPI, while delivering frontend static assets (`/`, `/css/*`, `/js/*`) directly from Vercel's global CDN.
- `.vercelignore`: Excludes test suites, virtual environments, and caches from the deployment artifact.

---

## API Documentation & Endpoints

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/` | No | Serves the web dashboard (`frontend/index.html`) |
| `GET` | `/health` | No | System health check (`{"status": "ok"}`) |
| `GET` | `/api` | No | API version and metadata |
| `POST` | `/login` | No | Validates credentials and returns a Bearer access token |
| `GET` | `/api/tank/summary` | No | Returns live level, min/max metrics, and historical logs |
| `GET` | `/device/{device_id}/status` | **Bearer Token** | Returns connectivity and staleness status of a device |

---

## Sample API Responses

### 1. `POST /login`
**Request Payload**:
```json
{
  "username": "demo",
  "password": "aqua123"
}
```

**Response (`200 OK`)**:
```json
{
  "access_token": "aquasense-demo-token",
  "token_type": "bearer"
}
```

### 2. `GET /api/tank/summary`
**Response (`200 OK`)**:
```json
{
  "current_level": 55.0,
  "minimum_level": 18.0,
  "maximum_level": 78.0,
  "active_alert": false,
  "historical_low_events": [
    {
      "timestamp": "2026-11-04T16:00:00+05:30",
      "level": 18.0
    }
  ],
  "readings": [
    { "timestamp": "2026-11-04T14:00:00+05:30", "level": 78.0 },
    { "timestamp": "2026-11-04T16:00:00+05:30", "level": 18.0 },
    { "timestamp": "2026-11-04T17:00:00+05:30", "level": 35.0 },
    { "timestamp": "2026-11-04T18:00:00+05:30", "level": 55.0 }
  ]
}
```

### 3. `GET /device/tank-001/status`
**Headers**: `Authorization: Bearer aquasense-demo-token`

**Response (`200 OK`)**:
```json
{
  "id": "tank-001",
  "online": true,
  "last_seen": "2026-11-04T12:00:00+05:30",
  "is_stale": false,
  "status": "online"
}
```

### 4. `GET /device/device-offline/status`
**Headers**: `Authorization: Bearer aquasense-demo-token`

**Response (`503 Service Unavailable`)**:
```json
{
  "detail": {
    "message": "Device is offline",
    "device_id": "device-offline"
  }
}
```

---

## Automated Testing

The automated test suite uses `pytest` and `fastapi.testclient.TestClient` to validate 16 independent test scenarios across authentication, device connectivity, malformed inputs, stale timestamps, and capacity boundary constraints (0% to 100%).

### Executing the Test Suite
From the project root:
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Test Coverage Breakdown
- `tests/test_login.py`:
  - `test_login_success`: Validates successful token generation.
  - `test_login_invalid_password`: Validates 401 unauthorized rejection.
  - `test_login_missing_fields`: Validates 422 payload validation errors.
- `tests/test_device_status.py`:
  - `test_device_status_valid_token`: Validates authenticated device inspection.
  - `test_device_status_invalid_token`: Validates 401 on bad bearer token.
  - `test_device_status_missing_token`: Validates 401 on missing header.
  - `test_device_status_nonexistent_device`: Validates 404 on unknown device ID.
  - `test_device_status_offline_device`: Validates 503 on offline hardware.
  - `test_device_status_malformed_record`: Validates 500 when record schema is corrupted.
  - `test_device_status_malformed_timestamp`: Validates 500 on unparseable date format.
  - `test_device_status_stale_timestamp`: Validates staleness detection when inactive > 24 hours.
- `tests/test_tank_levels.py`:
  - `test_tank_level_boundary_zero_percent_accepted`: Validates lower bound `0.0%`.
  - `test_tank_level_boundary_hundred_percent_accepted`: Validates upper bound `100.0%`.
  - `test_tank_level_boundary_below_zero_rejected`: Validates rejection of `< 0%`.
  - `test_tank_level_boundary_above_hundred_rejected`: Validates rejection of `> 100%`.
  - `test_tank_reading_model_boundary_validation`: Direct Pydantic model constraint checks.

---

## Assumptions and Limitations

1. **Authentication Scope**: The local build uses a deterministic demo credential pair (`demo` / `aqua123`) and a static bearer token (`aquasense-demo-token`). A production release would integrate OAuth2/OIDC with hashed passwords (e.g. Argon2/bcrypt) and signed JWTs.
2. **Data Persistence**: Telemetry is sourced from a static file (`data/mock_data.json`). In a physical IoT deployment, readings would be ingested via MQTT/CoAP into a time-series database (e.g., TimescaleDB, InfluxDB).
3. **Staleness Threshold**: Devices are deemed stale if their last recorded communication timestamp is older than 24 hours (`STALE_AFTER_SECONDS = 86400`).
4. **Safety Margin**: Tank levels strictly operate between `0.0%` and `100.0%`. A critical low alert is triggered whenever the current level drops below `20.0%`.

