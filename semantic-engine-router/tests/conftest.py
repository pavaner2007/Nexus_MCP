"""
tests/conftest.py
==================
Shared pytest fixtures and environment setup.

Injects a dummy SERPAPI_KEY into os.environ BEFORE any app module is
imported so tests pass on a fresh clone without a .env file.

IMPORTANT: pydantic-settings instantiates Settings() at module-import
time in app/config.py (module-level singleton).  pytest collects and
imports test modules *before* any fixture runs, so the env var must be
set here at the top level — not inside a fixture — to be available in
time.
"""

import os

# Set the key unconditionally at conftest import time.
# os.environ.setdefault will not overwrite a real key that may already be set
# (e.g. in CI or when a developer has a real .env loaded).
os.environ.setdefault("SERPAPI_KEY", "test_dummy_key_do_not_use_in_production")
