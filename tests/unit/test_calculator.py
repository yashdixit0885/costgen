"""T008 — deterministic cost calculator (100% coverage target) + C1 guard test."""

from __future__ import annotations

import pathlib
from decimal import Decimal

from costgen._engine.calculator import cost_for, price_usage
from costgen._engine.models import CacheTTL, Completeness, Origin, PricingRecord, Usage


def _record(**over):
    base = dict(
        provider="p",
        model="m",
        input_price_per_mtok=Decimal("5"),
        output_price_per_mtok=Decimal("25"),
        cache_write_multiplier={"5m": Decimal("1.25"), "1h": Decimal("2")},
        cache_read_multiplier=Decimal("0.1"),
        batch_discount=Decimal("0.5"),
        source="s",
        last_verified="2026-06-29",
        origin=Origin.BUNDLED,
    )
    base.update(over)
    return PricingRecord(**base)


def test_input_output_pricing_exact():
    # 1,000,000 input @ $5 + 1,000,000 output @ $25 = $30 exactly
    usage = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    assert price_usage(usage, _record()) == Decimal("30")


def test_partial_million_is_proportional():
    usage = Usage(input_tokens=500_000, output_tokens=0)
    assert price_usage(usage, _record()) == Decimal("2.5")


def test_cache_write_5m_and_1h_multipliers():
    rec = _record()
    w5 = price_usage(Usage(cache_write_tokens=1_000_000, cache_ttl=CacheTTL.FIVE_MIN), rec)
    w1h = price_usage(Usage(cache_write_tokens=1_000_000, cache_ttl=CacheTTL.ONE_HOUR), rec)
    assert w5 == Decimal("6.25")  # 5 * 1.25
    assert w1h == Decimal("10")  # 5 * 2
    # No TTL -> no write multiplier configured -> zero
    assert price_usage(Usage(cache_write_tokens=1_000_000, cache_ttl=CacheTTL.NONE), rec) == 0


def test_cache_read_multiplier():
    rec = _record()
    assert price_usage(Usage(cache_read_tokens=1_000_000), rec) == Decimal("0.5")  # 5 * 0.1


def test_batch_discount_applies():
    usage = Usage(input_tokens=1_000_000, output_tokens=0)
    assert price_usage(usage, _record(), batch=True) == Decimal("2.5")  # 5 * 0.5


def test_determinism_identical_inputs():
    usage = Usage(input_tokens=123, output_tokens=456, cache_read_tokens=7)
    rec = _record()
    assert price_usage(usage, rec) == price_usage(usage, rec)


def test_cost_for_empty_usage_is_incomplete():
    cost, status = cost_for(None, _record())
    assert cost is None and status is Completeness.INCOMPLETE


def test_cost_for_unknown_model_is_unpriced():
    cost, status = cost_for(Usage(input_tokens=10), None)
    assert cost is None and status is Completeness.UNPRICED


def test_cost_for_complete():
    cost, status = cost_for(Usage(input_tokens=1_000_000), _record())
    assert status is Completeness.COMPLETE and cost == Decimal("5")


def test_calculator_is_provider_agnostic():
    """C1 / Constitution II: the engine core must not branch on any vendor name."""
    source = pathlib.Path(
        __file__
    ).resolve().parents[2] / "src" / "costgen" / "_engine" / "calculator.py"
    text = source.read_text().lower()
    for vendor in ("anthropic", "openai", "claude", "gpt", "tiktoken", "bedrock", "vertex"):
        assert vendor not in text, f"calculator.py must not reference vendor {vendor!r}"
