# AI Usage and Collaboration Record

## 1. Assignment AI Usage Note (Concise Submission Note)

1. **Tool Used**: Google Antigravity coding assistant (powered by Claude 3.7 Sonnet and Gemini 3.8 Flash).
2. **Prompt 1**: *"Implement Phase 1 of the AquaSense assignment... make the backend fully compliant with the original Nivoryx assignment while preserving existing working functionality... GET /device/{id}/status response must include: level_percent, pump_state: 'on' or 'off', last_seen: timestamp."*
3. **Prompt 2**: *"Implement Phase 2 of AquaSense: Frontend Dashboard Correctness and Reliability... The dashboard must display: Current tank level, Minimum tank level, Maximum tank level, Last reading timestamp... Distinguish active alerts based on the latest reading from historical low-level events."*
4. **Genuine Mistake**: The AI initially used array index-based spacing (`index / (N - 1)`) for the SVG chart X-axis coordinates and concatenated unescaped strings into `innerHTML`. In Phase 3 tests, it also asserted a generic `"invalid tank reading"` string instead of asserting `data.py`'s exact exception message (`"Malformed tank reading"`).
5. **How Identified**: Code inspection revealed that irregular timestamp intervals (e.g., 06:00, 06:30, 20:00) were placed at equal intervals rather than proportionally, security review flagged dynamic `innerHTML`, and running `pytest -v` failed on the specific error message mismatch.
6. **How Corrected**: Replaced index-based positioning with linear epoch millisecond math `left + ((time - minTime) / (maxTime - minTime)) * plotWidth`, eliminated all `innerHTML` in favor of safe DOM methods (`document.createElement()`, `textContent`, `append()`), and updated test assertions to check exact domain error strings.

---

## 2. Detailed Development Log & Chronology

### Tools & Environment
- **Platform**: Google Antigravity Agentic IDE
- **Models**: Gemini 3.8 Flash (High) & Claude 3.7 Sonnet (Thinking)
- **Host System**: Windows 11 / Windows PowerShell / Python 3.15.2
- **Testing Engine**: Pytest 9.2.0, HTTPX 0.28.1, FastAPI TestClient, unittest.mock

---

### Detailed Prompt History & Engineering Stages

#### Stage 1: UI Redesign & Oceanic Aesthetic
- **Prompt**: *"okay go throught the UI files of my project and make some reallyy good looking UI, what I want is that I want you to make a welcome thing or something with aqua sense written on it and then the page comes up not directly the page make sure the UI is good follow some other aesthetic colour scheme and make sure that the UI looks really good and the backend works as it is"*
- **Result**: Designed the Oceanic Glassmorphism theme, added fluid wave SVG visualizers, radial capacity gauge, ambient mesh gradients, light/dark theme switching, and an interactive welcome screen.

#### Stage 2: Phase 1 Backend Timestamp & Schema Hardening
- **Prompt**: *"Now implement Phase 1 of the AquaSense assignment... make the backend fully compliant with the original Nivoryx assignment while preserving existing working functionality. GET /device/{id}/status response must include: level_percent, pump_state: 'on' or 'off', last_seen: timestamp."*
- **Result**: Normalized all internal timestamps to UTC, enforced timezone offsets on parse, rejected future timestamps beyond 300s clock drift, added `level_percent` and `pump_state` to `DeviceStatus`, updated mock data to 8 assignment readings from 2026-11-02, and ensured deterministic `AQUASENSE_REFERENCE_TIME` support.

#### Stage 3: Phase 2 Frontend Telemetry Accuracy & Security Hardening
- **Prompt**: *"Implement Phase 2 of AquaSense: Frontend Dashboard Correctness and Reliability. Preserve existing Oceanic Glassmorphism dashboard design... The dashboard must display: Current tank level, Minimum tank level, Maximum tank level, Last reading timestamp... Distinguish active alerts based on the latest reading from historical low-level events."*
- **Result**: Integrated live `/api/tank/summary` endpoints without hardcoded values, implemented strict payload validation (`validateTankSummary`, `validateDeviceStatus`), transitioned chart to linear time-based coordinates, separated API reachability from device hardware status, added stale telemetry indicators, and replaced `innerHTML` with safe DOM manipulation.

#### Stage 4: Phase 3 Comprehensive Automated Testing & Quality Assurance
- **Prompt**: *"Implement Phase 3: Comprehensive Automated Testing and Quality Assurance for AquaSense. Act as a Senior QA Automation Engineer... Categories: Authentication, Device Status, Tank Levels, Timestamps, Mocked API Responses... Assert both status codes and response bodies."*
- **Result**: Expanded the test suite to 92 automated tests across 6 test modules, achieving 100% statement and branch coverage of the backend application code.

---

### Genuine AI Errors, Diagnostics, and Resolutions

| Issue Category | Initial AI Behavior | Diagnostic / Failure | Resolution Applied |
| :--- | :--- | :--- | :--- |
| **Chart Spacing** | Used `left + (index / (N - 1)) * plotWidth` | Unequal time samples (e.g. 06:00, 06:30, 20:00) were placed at equal visual distances, falsely depicting a constant rate of drainage. | Refactored to linear time calculation: `left + ((t - min_t) / (max_t - min_t)) * plotWidth`. Single readings are centered at `393px`. |
| **XSS / Injection** | Dynamic HTML templating via `alert.innerHTML = ...` | Static code audit flagged potential DOM injection vector if untrusted reading values or timestamps were rendered. | Completely eliminated `innerHTML`. Replaced with `document.createElement()`, `textContent`, and `append()`. |
| **Windows Execution** | Executed `python -m pytest` globally | Failed with `ResourceUnavailable` because the global Windows Python launcher lacked installed venv packages. | Standardized all execution commands to target `.\.venv\Scripts\python.exe -m pytest`. |
| **Test Assertion Detail** | Asserted generic `"invalid tank reading"` | Pytest failed on `test_mocked_tank_summary_reading_not_dict` because `data.py` returned specific `"Malformed tank reading"`. | Hardened test assertions to match the precise, descriptive exception messages returned by the domain layer. |
