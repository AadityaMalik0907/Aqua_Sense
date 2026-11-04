"""Automated API tests for AquaSense user authentication (Category 1).

Covers:
1. Successful login.
2. Invalid password.
3. Invalid username.
4. Missing username.
5. Missing password.
6. Malformed login payload (empty dict, non-dict, wrong types, empty strings).
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_login_success():
    """Verify successful login with documented credentials returns a valid Bearer token."""
    response = client.post("/login", json={"username": "demo", "password": "aqua123"})
    
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "aquasense-demo-token"
    assert body["token_type"] == "bearer"


def test_login_invalid_password():
    """Verify login failure with an invalid password returns 401 Unauthorized."""
    response = client.post("/login", json={"username": "demo", "password": "wrongpassword"})
    
    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "Invalid username or password"
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_login_invalid_username():
    """Verify login failure with an unrecognized username returns 401 Unauthorized."""
    response = client.post("/login", json={"username": "unknown_operator", "password": "aqua123"})
    
    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "Invalid username or password"
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_login_missing_username():
    """Verify request with missing username field returns 422 Unprocessable Entity."""
    response = client.post("/login", json={"password": "aqua123"})
    
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(err.get("loc") == ["body", "username"] for err in body["detail"])


def test_login_missing_password():
    """Verify request with missing password field returns 422 Unprocessable Entity."""
    response = client.post("/login", json={"username": "demo"})
    
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(err.get("loc") == ["body", "password"] for err in body["detail"])


def test_login_missing_both_fields():
    """Verify validation rejection when credentials payload is an empty object."""
    response = client.post("/login", json={})
    
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(err.get("loc") == ["body", "username"] for err in body["detail"])
    assert any(err.get("loc") == ["body", "password"] for err in body["detail"])


@pytest.mark.parametrize(
    "malformed_payload",
    [
        {"username": "", "password": "aqua123"},       # Empty username violates min_length=1
        {"username": "demo", "password": ""},          # Empty password violates min_length=1
        {"username": 12345, "password": None},          # Invalid types
        {"username": ["demo"], "password": "aqua123"}, # Non-string username
    ],
)
def test_login_malformed_payload_types(malformed_payload):
    """Verify malformed login payloads with invalid field types or empty strings return 422."""
    response = client.post("/login", json=malformed_payload)
    assert response.status_code == 422
    assert "detail" in response.json()


def test_login_non_json_payload():
    """Verify sending non-JSON or raw text body returns 422 Unprocessable Entity."""
    response = client.post(
        "/login",
        content="raw-unformatted-string",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
