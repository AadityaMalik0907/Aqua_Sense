"""Mock authentication helpers for the AquaSense assignment."""

import os
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

# Default mock credentials, configurable via environment variables
MOCK_USERNAME = os.getenv("AQUASENSE_USERNAME", "demo")
MOCK_PASSWORD = os.getenv("AQUASENSE_PASSWORD", "aqua123")
MOCK_TOKEN = os.getenv("AQUASENSE_TOKEN", "aquasense-demo-token")


def authenticate(username: str, password: str) -> str:
    """Return the mock bearer token or raise 401 for invalid credentials."""
    if username != MOCK_USERNAME or password != MOCK_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    return MOCK_TOKEN


def require_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    """Validate a parsed bearer credential, rejecting missing and invalid tokens."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Bearer token required",
                            headers={"WWW-Authenticate": "Bearer"})
    if credentials.credentials != MOCK_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid bearer token",
                            headers={"WWW-Authenticate": "Bearer"})
    return credentials.credentials
