"""Keep the support-triage demo working: run it offline with costgen and assert
the cost story (Opus draft stage dominates) holds."""

from __future__ import annotations

import importlib.util
import pathlib
from decimal import Decimal

import costgen

_EXAMPLE_DIR = pathlib.Path(__file__).resolve().parents[1].parent / "examples" / "support_triage"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_demo_{name}", _EXAMPLE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_runs_offline_and_reports_expected_cost():
    offline = _load("_offline")
    existing_app = _load("existing_app")

    offline.enable()          # canned SDK responses, no network
    costgen.reset()
    costgen.install()         # the one line
    try:
        results = existing_app.process_tickets(existing_app.TICKETS)
    finally:
        costgen.uninstall()

    assert len(results) == 5

    report = costgen.get_report()
    # 5 tickets x 3 stages = 15 captured calls, all measured.
    calls = costgen.get_tracker().calls()
    assert len(calls) == 15
    assert all(c.measured_cost is not None for c in calls)

    # Two providers, three models; breakdowns sum to the grand total.
    assert set(report.by_provider) == {"openai", "anthropic"}
    assert set(report.by_model) == {"gpt-4o-mini", "claude-haiku-4-5", "claude-opus-4-8"}
    assert sum(report.by_model.values()) == report.grand_total
    assert report.grand_total > Decimal(0)

    # The Opus draft stage is the dominant cost (the demo's whole point).
    opus = report.by_model["claude-opus-4-8"]
    assert opus == max(report.by_model.values())
    assert opus / report.grand_total > Decimal("0.8")
