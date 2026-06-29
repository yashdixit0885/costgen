"""T020 — one-line auto-instrumentation produces correct measured totals."""

from __future__ import annotations

from decimal import Decimal

import costgen
from costgen._engine.models import CaptureSource, Completeness


def test_one_line_install_captures_calls(fake_sdk):
    costgen.install()
    client = fake_sdk.Client()
    client.create(model="demo-1", messages=[{"role": "user", "content": "hi"}])

    # 1000 input @ $1/MTok + 500 output @ $2/MTok = 0.001 + 0.001 = 0.002
    assert costgen.total() == Decimal("0.002")
    calls = costgen.get_tracker().calls()
    assert len(calls) == 1
    assert calls[0].capture_source is CaptureSource.AUTO
    assert calls[0].completeness is Completeness.COMPLETE
    assert calls[0].measured_cost is not None  # measured, not estimated
    assert calls[0].estimated_cost is None


def test_breakdown_by_model_present(fake_sdk):
    costgen.install()
    c = fake_sdk.Client()
    c.create(model="demo-1")
    c.create(model="demo-1")
    report = costgen.get_report()
    assert report.by_model["demo-1"] == Decimal("0.004")
    assert report.grand_total == sum(report.by_model.values())


def test_double_install_does_not_double_count(fake_sdk):
    costgen.install()
    costgen.install()  # idempotent — must not double-wrap
    fake_sdk.Client().create(model="demo-1")
    assert len(costgen.get_tracker().calls()) == 1


def test_uninstall_stops_capture(fake_sdk):
    costgen.install()
    costgen.uninstall()
    fake_sdk.Client().create(model="demo-1")
    assert costgen.get_tracker().calls() == []
