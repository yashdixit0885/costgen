"""T035 — estimation is distinct from measurement and doesn't pollute totals."""

from __future__ import annotations

from decimal import Decimal

import pytest

import costgen


def test_estimate_does_not_affect_measured_total(fake_provider):
    pytest.importorskip("tiktoken")
    costgen.reset()
    # A real measured call:
    costgen.record(provider="demo", model="demo-1",
                   usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}})
    measured_before = costgen.total()

    # An estimate is a prediction; it must NOT change the measured grand total.
    est = costgen.estimate(provider="openai", model="gpt-4o",
                           messages=[{"role": "user", "content": "estimate me"}],
                           assumed_output_tokens=100)
    assert est.kind == "estimate"
    assert costgen.total() == measured_before


def test_anthropic_and_openai_estimation_paths(fake_provider):
    pytest.importorskip("tiktoken")

    class FakeClient:
        class messages:
            @staticmethod
            def count_tokens(**kwargs):
                return type("C", (), {"input_tokens": 500_000})()

    a = costgen.estimate(provider="anthropic", model="claude-sonnet-4-6",
                         messages="hi", client=FakeClient())
    o = costgen.estimate(provider="openai", model="gpt-4o-mini",
                         messages=[{"role": "user", "content": "hi"}])

    assert a.assumptions["tokenizer"] == "anthropic.count_tokens"
    assert o.assumptions["tokenizer"] == "tiktoken"
    # sonnet-4-6 input $3/MTok * 0.5M = $1.50
    assert a.predicted_cost == Decimal("1.5")
    assert o.predicted_cost is not None
