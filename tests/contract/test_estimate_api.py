"""T034 — estimate() returns a labelled Estimate with reported assumptions."""

from __future__ import annotations

from decimal import Decimal

import pytest

import costgen


def test_estimate_openai_is_labelled_and_priced():
    pytest.importorskip("tiktoken")
    est = costgen.estimate(
        provider="openai", model="gpt-4o",
        messages=[{"role": "user", "content": "hello world " * 50}],
        assumed_output_tokens=200,
    )
    assert est.kind == "estimate"
    assert est.predicted_input_tokens > 0
    assert est.assumed_output_tokens == 200
    assert est.assumptions["tokenizer"] == "tiktoken"
    assert "assumed_output_tokens" in est.assumptions
    assert est.predicted_cost is not None and est.predicted_cost > 0


def test_estimate_unknown_model_unpriced_but_counts_tokens():
    pytest.importorskip("tiktoken")
    est = costgen.estimate(
        provider="openai", model="totally-unknown-model",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert est.predicted_input_tokens > 0
    assert est.predicted_cost is None  # no price -> unpriced, still labelled estimate


def test_estimate_rejects_unsupported_provider():
    with pytest.raises(ValueError):
        costgen.estimate(provider="cohere", model="x", messages="hi")


def test_estimate_anthropic_uses_count_tokens_via_injected_client():
    class FakeCount:
        def __init__(self, n):
            self.input_tokens = n

    class FakeMessages:
        def count_tokens(self, **kwargs):
            return FakeCount(1_000_000)

    class FakeClient:
        messages = FakeMessages()

    est = costgen.estimate(
        provider="anthropic", model="claude-opus-4-8",
        messages=[{"role": "user", "content": "x"}],
        assumed_output_tokens=0,
        client=FakeClient(),
    )
    assert est.assumptions["tokenizer"] == "anthropic.count_tokens"
    assert est.predicted_input_tokens == 1_000_000
    # opus-4-8 input $5/MTok -> $5 for 1M tokens
    assert est.predicted_cost == Decimal("5")
