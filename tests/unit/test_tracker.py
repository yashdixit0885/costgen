"""T010 — accumulation, dedupe, grouping, concurrency, breakdown invariants."""

from __future__ import annotations

import datetime as _dt
import threading
from decimal import Decimal

from costgen._engine.models import CaptureSource, Completeness, Origin, TrackedCall
from costgen._engine.tracker import CostTracker


def _call(cid, cost, *, provider="p", model="m", group=None, completeness=Completeness.COMPLETE):
    return TrackedCall(
        id=cid,
        provider=provider,
        model=model,
        usage=None,
        measured_cost=Decimal(str(cost)) if cost is not None else None,
        completeness=completeness,
        capture_source=CaptureSource.EXPLICIT,
        timestamp=_dt.datetime.now(_dt.UTC),
        group=group,
        pricing_origin=Origin.BUNDLED,
    )


def test_dedupe_by_id():
    t = CostTracker()
    assert t.record(_call("a", 1)) is not None
    assert t.record(_call("a", 1)) is None  # duplicate id ignored
    assert len(t.calls()) == 1


def test_total_sums_measured():
    t = CostTracker()
    t.record(_call("a", "1.5"))
    t.record(_call("b", "2.25"))
    assert t.total() == Decimal("3.75")


def test_breakdowns_sum_to_grand_total():
    t = CostTracker()
    t.record(_call("a", "1", provider="anthropic", model="x", group="g1"))
    t.record(_call("b", "2", provider="openai", model="y", group="g1"))
    t.record(_call("c", "3", provider="openai", model="y", group="g2"))
    r = t.get_report()
    assert r.grand_total == Decimal("6")
    assert sum(r.by_provider.values()) == r.grand_total
    assert sum(r.by_model.values()) == r.grand_total
    assert sum(g.total_cost for g in r.by_group) == r.grand_total


def test_incomplete_and_unpriced_counts():
    t = CostTracker()
    t.record(_call("a", None, completeness=Completeness.INCOMPLETE))
    t.record(_call("b", None, completeness=Completeness.UNPRICED))
    r = t.get_report()
    assert r.incomplete_count == 1
    assert r.unpriced_count == 1
    assert r.grand_total == Decimal("0")


def test_concurrent_records_no_loss():
    t = CostTracker()
    n = 200

    def worker(i):
        t.record(_call(f"id-{i}", "0.01"))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert len(t.calls()) == n
    assert t.total() == Decimal("0.01") * n


def test_reset_clears():
    t = CostTracker()
    t.record(_call("a", "1"))
    t.reset()
    assert t.calls() == [] and t.total() == Decimal("0")
