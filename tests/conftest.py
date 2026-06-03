"""Pytest setup for the golden dataset.

If the ADK agent is already reachable at $ADK_URL (default
http://localhost:8080), tests reuse it as-is — no Docker action.

Otherwise, the session-scoped fixture brings up the `adk-agent` service
from docker-compose.yaml for the duration of the test session, then
shuts it down on teardown.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

ADK_URL = os.environ.get("ADK_URL", "http://localhost:8080")
PROJECT_ROOT = Path(__file__).parent.parent
COMPOSE_SERVICE = "adk-agent"
READINESS_TIMEOUT_SECONDS = 180


def _adk_responds(url: str = ADK_URL, timeout: float = 2.0) -> bool:
    try:
        with urlopen(f"{url}/docs", timeout=timeout) as response:
            return response.status == 200
    except (URLError, TimeoutError, OSError):
        return False


def _wait_until_ready(url: str = ADK_URL, deadline_seconds: int = READINESS_TIMEOUT_SECONDS) -> None:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        if _adk_responds(url):
            return
        time.sleep(2)
    raise RuntimeError(f"ADK at {url} not ready within {deadline_seconds}s")


@pytest.fixture(scope="session", autouse=True)
def adk_agent_lifecycle():
    """Ensure the ADK agent is reachable for the test session."""
    if _adk_responds():
        print(f"\n→ Reusing already-running ADK at {ADK_URL}")
        yield
        return

    print(f"\n→ ADK not reachable, starting `docker compose up -d {COMPOSE_SERVICE}` ...")
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", COMPOSE_SERVICE],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        pytest.skip("`docker` not installed — start the ADK agent manually before running the tests.")
    except subprocess.CalledProcessError as exc:
        pytest.fail(f"docker compose failed: {exc.stderr.decode(errors='replace')}")

    try:
        _wait_until_ready()
        print(f"→ ADK is ready at {ADK_URL}")
        yield
    finally:
        print(f"\n→ Tearing down compose service `{COMPOSE_SERVICE}`")
        subprocess.run(
            ["docker", "compose", "down"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
        )
