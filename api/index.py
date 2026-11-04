"""Vercel serverless entrypoint for AquaSense FastAPI application."""

import sys
from pathlib import Path

# Add project root directory to sys.path so 'backend' package imports reliably
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.main import app

# Expose 'app' as the ASGI application for Vercel serverless runtime
__all__ = ["app"]

