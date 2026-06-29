"""T012 — pricing load, provenance enforcement, override resolution, freshness."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from costgen._engine.models import PricingRecord
from costgen._pricing import loader as pricing
from costgen._pricing.base import PricingRegistry
from costgen._pricing.loader import load_bundled


def test_bundled_anthropic_and_openai_loaded():
    reg = load_bundled()
    assert reg.lookup("anthropic", "claude-opus-4-8").input_price_per_mtok == Decimal("5.00")
    assert reg.lookup("openai", "gpt-4o").output_price_per_mtok == Decimal("10.00")


def test_every_bundled_record_has_provenance():
    reg = load_bundled()
    for store in (reg._bundled,):
        for rec in store.values():
            assert rec.source
            assert rec.last_verified


def test_missing_source_rejected():
    with pytest.raises(ValueError):
        PricingRecord(
            provider="p",
            model="m",
            input_price_per_mtok=Decimal("1"),
            output_price_per_mtok=Decimal("2"),
            source="",
            last_verified="2026-06-29",
        )


def test_missing_last_verified_rejected():
    with pytest.raises(ValueError):
        PricingRecord(
            provider="p",
            model="m",
            input_price_per_mtok=Decimal("1"),
            output_price_per_mtok=Decimal("2"),
            source="x",
            last_verified="",
        )


def test_override_beats_bundled():
    reg = PricingRegistry()
    reg.add_bundled(
        PricingRecord(
            provider="p", model="m",
            input_price_per_mtok=Decimal("5"), output_price_per_mtok=Decimal("25"),
            source="bundled", last_verified="2026-01-01",
        )
    )
    reg.set_override(
        provider="p", model="m",
        input_price_per_mtok="4", output_price_per_mtok="20",
        source="contract", last_verified="2026-06-01",
    )
    rec = reg.lookup("p", "m")
    assert rec.input_price_per_mtok == Decimal("4")
    assert rec.source == "contract"


def test_set_price_requires_provenance():
    reg = PricingRegistry()
    with pytest.raises(ValueError):
        reg.set_override(
            provider="p", model="m",
            input_price_per_mtok="4", output_price_per_mtok="20",
            source="", last_verified="2026-06-01",
        )


def test_freshness_returns_earliest():
    reg = load_bundled()
    assert reg.freshness("anthropic") == "2026-06-29"


def test_load_prices_from_file(tmp_path):
    f = tmp_path / "prices.json"
    f.write_text(
        json.dumps(
            {
                "provider": "demo",
                "source": "file",
                "last_verified": "2026-06-29",
                "records": [
                    {"model": "d1", "input_price_per_mtok": "9", "output_price_per_mtok": "9"}
                ],
            }
        )
    )
    pricing.load_prices(str(f))
    rec = pricing.lookup("demo", "d1")
    assert rec is not None and rec.input_price_per_mtok == Decimal("9")
    # cleanup the process-wide override
    pricing.get_registry()._overrides.pop(("demo", "d1"), None)
