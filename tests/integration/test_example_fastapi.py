"""Keep the FastAPI cost-aware demo working: drive it with TestClient offline and
assert per-request cost, the /costs endpoint, and the budget guard (429)."""

from __future__ import annotations

import importlib
import pathlib
import sys
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("anthropic")
from fastapi.testclient import TestClient  # noqa: E402

_EXAMPLE_DIR = pathlib.Path(__file__).resolve().parents[1].parent / "examples"


@pytest.fixture
def client(monkeypatch):
    # Make example modules importable.
    monkeypatch.syspath_prepend(str(_EXAMPLE_DIR))
    monkeypatch.syspath_prepend(str(_EXAMPLE_DIR / "fastapi_service"))

    # Patch the SDK offline BEFORE importing app (so install() wraps the stub).
    from _offline_providers import patch_anthropic, unpatch_anthropic

    patch_anthropic(lambda model, kwargs: {
        "text": "answer", "input_tokens": 1500, "output_tokens": 200, "cache_read": 0,
    })
    # Tight budget so the guard trips quickly in the test.
    monkeypatch.setenv("COSTGEN_BUDGET_USD", "0.005")

    sys.modules.pop("app", None)
    app_module = importlib.import_module("app")

    import costgen
    costgen.reset()
    try:
        yield TestClient(app_module.app)
    finally:
        unpatch_anthropic()
        sys.modules.pop("app", None)


def test_chat_returns_per_request_cost(client):
    r = client.post("/chat", json={"user": "alice", "question": "hi"})
    assert r.status_code == 200
    body = r.json()
    # haiku-4-5: 1500 input @ $1 + 200 output @ $5 per MTok = 0.0015 + 0.001
    assert Decimal(body["request_cost_usd"]) == Decimal("0.0025")
    assert Decimal(body["total_cost_usd"]) == Decimal("0.0025")


def test_costs_endpoint_breaks_down_by_user(client):
    client.post("/chat", json={"user": "alice", "question": "q1"})
    client.post("/chat", json={"user": "bob", "question": "q2"})
    costs = client.get("/costs").json()
    assert set(costs["by_user"]) == {"alice", "bob"}
    assert Decimal(costs["total_usd"]) == Decimal("0.005")
    assert costs["calls"] == 2


def test_budget_guard_returns_429(client):
    # Budget is $0.005; each call is $0.0025 -> the 3rd call must be refused.
    assert client.post("/chat", json={"user": "alice", "question": "q"}).status_code == 200
    assert client.post("/chat", json={"user": "alice", "question": "q"}).status_code == 200
    blocked = client.post("/chat", json={"user": "alice", "question": "q"})
    assert blocked.status_code == 429
    assert "budget" in blocked.json()["detail"].lower()
