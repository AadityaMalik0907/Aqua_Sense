# AquaSense - Test Cases & Automated Verification Report

This document records the automated test cases designed and executed for the AquaSense API using `pytest` and FastAPI's `TestClient`. All test cases were executed against the local test harness and verified without requiring physical IoT hardware or external network calls.

---

## Test Execution Summary

- **Total Test Cases**: 16
- **Passed**: 16
- **Failed**: 0
- **Execution Date**: 2026-11-04
- **Test Runner**: `pytest` 9.2.0 / `TestClient` (Starlette/HTTPX) on Python 3.15.2 (Windows)

---

## Detailed Test Cases

### TC-001: Successful User Authentication
- **Test ID**: `TC-001`
- **Description**: Verify that providing valid mock credentials returns a valid Bearer access token.
- **Preconditions**: AquaSense FastAPI server is initialized with mock authentication service.
- **Input**:
  - Method: `POST`
  - URL: `/login`
  - Headers: `Content-Type: application/json`
  - Body: `{"username": "demo", "password": "aqua123"}`
- **Expected Result**:
  - Status Code: `200 OK`
  - Body: `{"access_token": "aquasense-demo-token", "token_type": "bearer"}`
- **Actual Result**:
  - Status Code: `200 OK`
  - Body: `{"access_token": "aquasense-demo-token", "token_type": "bearer"}`
- **Status**: **PASS**

---

### TC-002: Login with Invalid Password
- **Test ID**: `TC-002`
- **Description**: Verify that providing an incorrect password rejects authentication with HTTP 401.
- **Preconditions**: Server is running.
- **Input**:
  - Method: `POST`
  - URL: `/login`
  - Headers: `Content-Type: application/json`
  - Body: `{"username": "demo", "password": "wrongpassword"}`
- **Expected Result**:
  - Status Code: `401 Unauthorized`
  - Body: `{"detail": "Invalid username or password"}`
- **Actual Result**:
  - Status Code: `401 Unauthorized`
  - Body: `{"detail": "Invalid username or password"}`
- **Status**: **PASS**

---

### TC-003: Login Payload Validation Failure
- **Test ID**: `TC-003`
- **Description**: Verify that omitting required credential fields triggers request body validation error.
- **Preconditions**: Server is running.
- **Input**:
  - Method: `POST`
  - URL: `/login`
  - Headers: `Content-Type: application/json`
  - Body: `{}`
- **Expected Result**:
  - Status Code: `422 Unprocessable Entity`
  - Body: Contains validation errors specifying missing `username` and `password` body fields.
- **Actual Result**:
  - Status Code: `422 Unprocessable Entity`
  - Body: Field errors located at `['body', 'username']` and `['body', 'password']`.
- **Status**: **PASS**

---

### TC-004: Access Device Status with Valid Bearer Token
- **Test ID**: `TC-004`
- **Description**: Verify that an authenticated user can inspect the telemetry status of an active online device.
- **Preconditions**: Mock data contains device `tank-001` with `online: true` and recent timestamp.
- **Input**:
  - Method: `GET`
  - URL: `/device/tank-001/status`
  - Headers: `Authorization: Bearer aquasense-demo-token`
- **Expected Result**:
  - Status Code: `200 OK`
  - Body: Contains `id: "tank-001"`, `online: true`, `status: "online"`, `is_stale: false`, and an ISO 8601 `last_seen` timestamp.
- **Actual Result**:
  - Status Code: `200 OK`
  - Body: `{"id": "tank-001", "online": true, "last_seen": "2026-11-04T12:00:00+05:30", "is_stale": false, "status": "online"}`
- **Status**: **PASS**

---

### TC-005: Access Device Status with Invalid Bearer Token
- **Test ID**: `TC-005`
- **Description**: Verify that a malformed or invalid token is rejected with HTTP 401.
- **Preconditions**: Server is running.
- **Input**:
  - Method: `GET`
  - URL: `/device/tank-001/status`
  - Headers: `Authorization: Bearer invalid-token-xyz`
- **Expected Result**:
  - Status Code: `401 Unauthorized`
  - Body: `{"detail": "Invalid bearer token"}`
- **Actual Result**:
  - Status Code: `401 Unauthorized`
  - Body: `{"detail": "Invalid bearer token"}`
- **Status**: **PASS**

---

### TC-006: Access Device Status Without Authorization Header
- **Test ID**: `TC-006`
- **Description**: Verify that requests missing the Authorization header are rejected.
- **Preconditions**: Server is running.
- **Input**:
  - Method: `GET`
  - URL: `/device/tank-001/status`
  - Headers: None
- **Expected Result**:
  - Status Code: `401 Unauthorized`
  - Body: `{"detail": "Bearer token required"}`
- **Actual Result**:
  - Status Code: `401 Unauthorized`
  - Body: `{"detail": "Bearer token required"}`
- **Status**: **PASS**

---

### TC-007: Request Status of Nonexistent Device ID
- **Test ID**: `TC-007`
- **Description**: Verify that querying an unregistered device ID returns HTTP 404 Not Found.
- **Preconditions**: Authenticated with valid Bearer token.
- **Input**:
  - Method: `GET`
  - URL: `/device/nonexistent-device-999/status`
  - Headers: `Authorization: Bearer aquasense-demo-token`
- **Expected Result**:
  - Status Code: `404 Not Found`
  - Body: `{"detail": "Device not found"}`
- **Actual Result**:
  - Status Code: `404 Not Found`
  - Body: `{"detail": "Device not found"}`
- **Status**: **PASS**

---

### TC-008: Handle Device in Offline State
- **Test ID**: `TC-008`
- **Description**: Verify that inspecting an offline device raises an explicit HTTP 503 Service Unavailable alert.
- **Preconditions**: Mock dataset has device `device-offline` configured with `online: false`.
- **Input**:
  - Method: `GET`
  - URL: `/device/device-offline/status`
  - Headers: `Authorization: Bearer aquasense-demo-token`
- **Expected Result**:
  - Status Code: `503 Service Unavailable`
  - Body: `{"detail": {"message": "Device is offline", "device_id": "device-offline"}}`
- **Actual Result**:
  - Status Code: `503 Service Unavailable`
  - Body: `{"detail": {"message": "Device is offline", "device_id": "device-offline"}}`
- **Status**: **PASS**

---

### TC-009: Handle Malformed Device Record (Non-Boolean Online Value)
- **Test ID**: `TC-009`
- **Description**: Verify that if persistent storage holds a corrupt record where `online` is non-boolean, a safe 500 server error is returned.
- **Preconditions**: Mock storage returns record with `"online": "not-a-boolean"`.
- **Input**:
  - Method: `GET`
  - URL: `/device/device-malformed/status`
  - Headers: `Authorization: Bearer aquasense-demo-token`
- **Expected Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Device record is malformed"}`
- **Actual Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Device record is malformed"}`
- **Status**: **PASS**

---

### TC-010: Handle Malformed Device Timestamp Format
- **Test ID**: `TC-010`
- **Description**: Verify that corrupt or unparseable date strings for `last_seen` raise a 500 error.
- **Preconditions**: Mock storage returns record with `"last_seen": "invalid-non-iso-timestamp"`.
- **Input**:
  - Method: `GET`
  - URL: `/device/device-bad-date/status`
  - Headers: `Authorization: Bearer aquasense-demo-token`
- **Expected Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Device last_seen is malformed"}`
- **Actual Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Device last_seen is malformed"}`
- **Status**: **PASS**

---

### TC-011: Handle Stale Device Timestamp (> 24 Hours Inactive)
- **Test ID**: `TC-011`
- **Description**: Verify that a device whose last reading was over 24 hours ago is flagged with `is_stale: true` and `status: "stale"`.
- **Preconditions**: Mock storage contains device `device-stale` with `last_seen` dated older than 24 hours.
- **Input**:
  - Method: `GET`
  - URL: `/device/device-stale/status`
  - Headers: `Authorization: Bearer aquasense-demo-token`
- **Expected Result**:
  - Status Code: `200 OK`
  - Body: `id: "device-stale"`, `online: true`, `is_stale: true`, `status: "stale"`.
- **Actual Result**:
  - Status Code: `200 OK`
  - Body: `{"id": "device-stale", "online": true, "last_seen": "2026-10-01T10:00:00+05:30", "is_stale": true, "status": "stale"}`
- **Status**: **PASS**

---

### TC-012: Tank Level Boundary - Lower Bound 0% Accepted
- **Test ID**: `TC-012`
- **Description**: Verify that a reading at exactly 0.0% capacity is accepted and triggers the active low-level alert.
- **Preconditions**: Mock data returns tank reading with `level: 0.0`.
- **Input**:
  - Method: `GET`
  - URL: `/api/tank/summary`
- **Expected Result**:
  - Status Code: `200 OK`
  - Body: `current_level: 0.0`, `minimum_level: 0.0`, `active_alert: true`, readings array contains `0.0`.
- **Actual Result**:
  - Status Code: `200 OK`
  - Body: `current_level: 0.0`, `minimum_level: 0.0`, `active_alert: true`.
- **Status**: **PASS**

---

### TC-013: Tank Level Boundary - Upper Bound 100% Accepted
- **Test ID**: `TC-013`
- **Description**: Verify that a reading at exactly 100.0% capacity is accepted as safe normal operation.
- **Preconditions**: Mock data returns tank reading with `level: 100.0`.
- **Input**:
  - Method: `GET`
  - URL: `/api/tank/summary`
- **Expected Result**:
  - Status Code: `200 OK`
  - Body: `current_level: 100.0`, `maximum_level: 100.0`, `active_alert: false`.
- **Actual Result**:
  - Status Code: `200 OK`
  - Body: `current_level: 100.0`, `maximum_level: 100.0`, `active_alert: false`.
- **Status**: **PASS**

---

### TC-014: Tank Level Boundary - Value Below 0% Rejected
- **Test ID**: `TC-014`
- **Description**: Verify that invalid negative levels (e.g. -1.0%) are rejected with HTTP 500 error.
- **Preconditions**: Storage contains invalid negative reading.
- **Input**:
  - Method: `GET`
  - URL: `/api/tank/summary`
- **Expected Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Tank reading level must be between 0 and 100"}`
- **Actual Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Tank reading level must be between 0 and 100"}`
- **Status**: **PASS**

---

### TC-015: Tank Level Boundary - Value Above 100% Rejected
- **Test ID**: `TC-015`
- **Description**: Verify that capacity levels exceeding 100% (e.g. 100.5%) are rejected with HTTP 500 error.
- **Preconditions**: Storage contains out-of-bounds reading.
- **Input**:
  - Method: `GET`
  - URL: `/api/tank/summary`
- **Expected Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Tank reading level must be between 0 and 100"}`
- **Actual Result**:
  - Status Code: `500 Internal Server Error`
  - Body: `{"detail": "Tank reading level must be between 0 and 100"}`
- **Status**: **PASS**

---

### TC-016: Pydantic Data Model Level Boundary Constraints
- **Test ID**: `TC-016`
- **Description**: Verify direct programmatic validation in `TankReading(timestamp, level)` model enforcing `ge=0` and `le=100`.
- **Preconditions**: Import `TankReading` from `backend.app.models`.
- **Input**: Instances created with `level=0`, `level=100`, `level=-0.1`, and `level=100.1`.
- **Expected Result**: Levels 0 and 100 instantiate without error; levels -0.1 and 100.1 raise `pydantic.ValidationError`.
- **Actual Result**: Lower and upper valid bounds succeeded; negative and overflow bounds raised `ValidationError`.
- **Status**: **PASS**
