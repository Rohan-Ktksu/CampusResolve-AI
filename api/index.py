"""Vercel serverless entry point: serves the FastAPI backend for /api/* requests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402,F401  (Vercel looks for `app`)

# Serverless runtimes may skip ASGI lifespan events; table creation and seed config are idempotent.
init_db()
