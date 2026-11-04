"""Automated API tests for AquaSense user authentication."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_login_success():
    """Scenario 1: Successful login with valid credentials."""
    response = client.post("/login", json={"username": "demo", "password": "aqua123"})
    
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "aquasense-demo-token"
    assert body["token_type"] == "bearer"


def test_login_invalid_password():
    """Scenario 2: Login failure with an invalid password."""
    response = client.post("/login", json={"username": "demo", "password": "wrongpassword"})
    
    assert response.status_code == 401
    body = response.json()
    assert body["detail"] == "Invalid username or password"


def test_login_missing_fields():
    """Verify validation rejection when credentials are missing."""
    response = client.post("/login", json={})
    
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert any(err.get("loc") == ["body", "username"] for err in body["detail"])
    assert any(err.get("loc") == ["body", "password"] for err in body["detail"])
