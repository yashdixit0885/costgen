"""Keep the estimate-router demo working: short prompt stays premium, large one is
downgraded before sending (offline)."""

from __future__ import annotations

import importlib.util
import pathlib
from decimal import Decimal

import pytest

import costgen

pytest.importorskip("tiktoken")
pytest.importorskip("openai")

_DIR = pathlib.Path(__file__).resolve().parents[1].parent / "examples" / "estimate_router"
_EXAMPLES = _DIR.parent


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def offline_client(monkeypatch):
    monkeypatch.syspath_prepend(str(_EXAMPLES))
    from _offline_providers import openai_offline_http_client
    from openai import OpenAI

    def profile(model, body):
        msgs = body.get("messages", [])
        text = " ".join(m.get("content", "") for m in msgs if isinstance(m.get("content"), str))
        return {"text": "answer", "input_tokens": max(len(text) // 4, 1), "output_tokens": 120}

    client = OpenAI(api_key="sk-offline", http_client=openai_offline_http_client(profile))
    costgen.install()
    costgen.reset()
    yield client
    costgen.uninstall()


def test_router_keeps_short_prompt_premium_and_downgrades_large(offline_client):
    router = _load(_DIR / "router.py", "_demo_router")
    cap = Decimal("0.004")

    short_model, short_est, _ = router.route_and_answer(
        offline_client, "Define idempotency in one sentence.", per_request_cap_usd=cap
    )
    long_model, long_est, _ = router.route_and_answer(
        offline_client, "Summarize this. " + "context line. " * 6000, per_request_cap_usd=cap
    )

    assert short_est.kind == "estimate"
    assert short_model == router.PREMIUM           # cheap enough -> premium
    assert long_model == router.CHEAP              # too expensive -> downgraded
    assert long_est.predicted_cost > cap
    # Two real (measured) sends were captured.
    assert len(costgen.get_tracker().calls()) == 2
