"""T027 — report breakdowns by provider/model/group sum to the grand total."""

from __future__ import annotations

import costgen
from costgen import track


def _emit(model, group=None):
    with track(group) if group else _null():
        costgen.record(
            provider="demo", model=model,
            usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}},
        )


class _null:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_breakdowns_sum_and_render(fake_provider):
    costgen.reset()
    costgen.record(provider="demo", model="demo-1", group="search",
                   usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}})
    costgen.record(provider="demo", model="demo-1", group="summarize",
                   usage={"usage": {"input_tokens": 2_000_000, "output_tokens": 0}})

    report = costgen.get_report()
    assert report.grand_total == sum(report.by_provider.values())
    assert report.grand_total == sum(report.by_model.values())
    assert report.grand_total == sum(g.total_cost for g in report.by_group)

    groups = {g.name for g in report.by_group}
    assert {"search", "summarize"} <= groups

    text = costgen.report()
    assert "Grand total" in text
    assert "search" in text and "summarize" in text


def test_pricing_freshness_surfaced(fake_provider):
    costgen.reset()
    costgen.record(provider="demo", model="demo-1",
                   usage={"usage": {"input_tokens": 1, "output_tokens": 0}})
    report = costgen.get_report()
    assert report.pricing_freshness.get("demo") == "2026-06-29"
