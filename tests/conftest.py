"""Shared fixtures.

`fake_provider` registers a fully controlled provider ("demo") — a usage
normalizer + a bundled price — so adapter/pipeline behaviour can be tested
deterministically without depending on real SDK internals or pricing drift.
"""

from __future__ import annotations

import sys
import types
from decimal import Decimal

import pytest

from costgen._adapters import instrument, normalize
from costgen._engine.models import Origin, PricingRecord, Usage
from costgen._engine.tracker import get_tracker
from costgen._pricing import loader as pricing


@pytest.fixture(autouse=True)
def _reset_tracker():
    get_tracker().reset()
    yield
    get_tracker().reset()


def _demo_parser(raw):
    usage = raw.get("usage", raw) if isinstance(raw, dict) else raw
    if usage is None:
        return None
    if "input_tokens" not in usage and "output_tokens" not in usage:
        return None
    return Usage(
        input_tokens=int(usage.get("input_tokens", 0)),
        output_tokens=int(usage.get("output_tokens", 0)),
    )


@pytest.fixture
def fake_provider():
    """Register provider 'demo' (model 'demo-1': $1/$2 per MTok). Yields the parser
    registry so a test can swap in a raising parser to exercise the guard."""
    normalize._PARSERS["demo"] = _demo_parser
    registry = pricing.get_registry()
    registry.add_bundled(
        PricingRecord(
            provider="demo",
            model="demo-1",
            input_price_per_mtok=Decimal("1.00"),
            output_price_per_mtok=Decimal("2.00"),
            source="test",
            last_verified="2026-06-29",
            origin=Origin.BUNDLED,
        )
    )
    try:
        yield normalize._PARSERS
    finally:
        normalize._PARSERS.pop("demo", None)
        registry._bundled.pop(("demo", "demo-1"), None)


@pytest.fixture
def fake_sdk(fake_provider):
    """A fake provider SDK ('demo_sdk.Client.create') registered as a costgen
    patch target, so the auto-instrument machinery can be tested without any
    real SDK. Default response: 1000 input / 500 output for model 'demo-1'."""

    class Client:
        resp = {"usage": {"input_tokens": 1000, "output_tokens": 500}, "model": "demo-1"}

        def create(self, **kwargs):
            return getattr(self, "resp", type(self).resp)

    module = types.ModuleType("demo_sdk")
    module.Client = Client
    sys.modules["demo_sdk"] = module

    spec = instrument.PatchSpec("demo", "demo_sdk", "Client.create", "kwargs")
    instrument._SPECS.append(spec)
    try:
        yield module
    finally:
        instrument.uninstall()
        if spec in instrument._SPECS:
            instrument._SPECS.remove(spec)
        sys.modules.pop("demo_sdk", None)
