"""Vercel ASGI entrypoint; all /api requests preserve their original path."""
import os
os.environ.setdefault('ARTIFACT_STORAGE','database')
os.environ.setdefault('COOKIE_SECURE','true')
from backend.app.main import app
