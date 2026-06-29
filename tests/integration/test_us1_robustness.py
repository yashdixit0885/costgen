"""T022 — edge cases & the non-intrusive guarantee (Constitution III)."""

from __future__ import annotations

import threading
from decimal import Decimal

import costgen
from costgen._adapters import normalize
from costgen._engine.models import Completeness


def test_missing_usage_recorded_incomplete_not_zero(fake_sdk):
    costgen.install()
    c = fake_sdk.Client()
    c.resp = {"usage": {}, "model": "demo-1"}  # provider returned no usable usage
    c.create(model="demo-1")
    calls = costgen.get_tracker().calls()
    assert len(calls) == 1
    assert calls[0].completeness is Completeness.INCOMPLETE
    assert calls[0].measured_cost is None
    assert costgen.total() == Decimal("0")  # never priced as zero silently
    assert costgen.get_report().incomplete_count == 1


def test_unknown_model_recorded_unpriced(fake_sdk):
    costgen.install()
    c = fake_sdk.Client()
    c.resp = {"usage": {"input_tokens": 10, "output_tokens": 5}, "model": "ghost"}
    c.create(model="ghost")
    report = costgen.get_report()
    assert report.unpriced_count == 1
    assert report.grand_total == Decimal("0")


def test_internal_error_never_raises_into_host(fake_sdk):
    costgen.install()
    # Force the observation path to blow up; the host call must be unaffected.
    normalize._PARSERS["demo"] = lambda raw: (_ for _ in ()).throw(RuntimeError("boom"))
    c = fake_sdk.Client()
    response = c.create(model="demo-1")  # must NOT raise
    assert response["model"] == "demo-1"
    assert costgen.total() == Decimal("0")


def test_concurrent_calls_sum_equals_total(fake_sdk):
    costgen.install()
    n = 100

    def worker():
        fake_sdk.Client().create(model="demo-1")

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(costgen.get_tracker().calls()) == n
    assert costgen.total() == Decimal("0.002") * n
