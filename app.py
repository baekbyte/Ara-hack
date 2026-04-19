"""Ara automation entrypoint for Memory Palace.

Local run notes:
- Start the FastAPI bridge first: `uvicorn server:app --reload`
- For Ara local development, use `ara run app.py`
- For deployment, use `ara auth login` then `ara deploy app.py`
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:  # pragma: no cover - Ara SDK is optional during local backend testing
    from ara_sdk import Automation, env, secret, tool
except ImportError:  # pragma: no cover
    def env(name: str, default: str | None = None) -> str | None:
        return os.getenv(name, default)

    def secret(name: str, default: str | None = None) -> str | None:
        return os.getenv(name, default)

    def tool(func):  # type: ignore[no-untyped-def]
        return func

    class Automation:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs


import sys, os; sys.path.insert(0, os.path.dirname(__file__))
from prompts import MEMORY_PALACE_SYSTEM_INSTRUCTIONS


API_BASE = env("MEMORY_PALACE_API_BASE", "http://localhost:8000") or "http://localhost:8000"
API_TOKEN = secret("MEMORY_PALACE_API_TOKEN", "dev-token") or "dev-token"


def _headers() -> dict[str, str]:
    return {"X-API-Token": API_TOKEN}


@tool
def query_memory_palace(question: str) -> dict:
    """Retrieve compact personalized context from the Memory Palace graph."""
    response = httpx.get(
        f"{API_BASE}/query",
        params={"q": question},
        headers=_headers(),
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()


@tool
def log_ara_action(action_type: str, content: str, metadata: dict | None = None) -> dict:
    """Persist Ara's own actions back into the Memory Palace graph."""
    response = httpx.post(
        f"{API_BASE}/webhook/ara/action",
        json={
            "action_type": action_type,
            "content": content,
            "metadata": metadata or {},
        },
        headers=_headers(),
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()


memory_palace_agent = Automation(
    "memory-palace-agent",
    system_instructions=MEMORY_PALACE_SYSTEM_INSTRUCTIONS,
    tools=[query_memory_palace, log_ara_action],
    allow_connector_tools=True,
    required_env=["MEMORY_PALACE_API_BASE"],
)
