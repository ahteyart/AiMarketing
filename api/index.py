"""
Vercel Python serverless entry point.
This file exposes the FastAPI app as a Vercel Python function.
All /api/* routes are handled here.

Vercel routes: /api/(.*) → api/index.py
"""

import sys
import os

# Add backend to Python path so app imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402 — must come after sys.path modification

# Vercel looks for 'app' or 'handler' as the ASGI entry point
handler = app
