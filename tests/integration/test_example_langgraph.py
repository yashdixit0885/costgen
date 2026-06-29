"""Keep the LangGraph agent demo working: run it offline and assert per-node
cost attribution + the cost story (synthesize/Opus dominates)."""

from __future__ import annotations

import importlib.util
import pathlib
from decimal import Decimal

import pytest

import costgen

pytest.importorskip("langgraph")
pytest.importorskip("langchain_openai")
pytest.importorskip("langchain_anthropic")

_RUN = (
    pathlib.Path(__file__).resolve().parents[1].parent
    / "examples" / "langgraph_agent" / "run.py"
)


def _load_run():
    spec = importlib.util.spec_from_file_location("_demo_lg_run", _RUN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_langgraph_demo_offline_per_node_cost():
    run = _load_run()
    try:
        plan_llm, research_llm, synth_llm = run._offline_llms()
        app = run.build_agent(plan_llm, research_llm, synth_llm)

        costgen.reset()
        result = app.invoke({"question": run.QUESTION})
        assert result["answer"]

        report = costgen.get_report()
        calls = costgen.get_tracker().calls()
        assert len(calls) == 3  # plan + research + synthesize

        groups = {g.name: g.total_cost for g in report.by_group}
        assert set(groups) == {"plan", "research", "synthesize"}
        # The synthesize node (Opus) is the dominant cost.
        assert groups["synthesize"] == max(groups.values())
        assert groups["synthesize"] / report.grand_total > Decimal("0.8")

        # Cross-provider, cross-model capture via the callback.
        assert set(report.by_provider) == {"openai", "anthropic"}
        assert sum(report.by_model.values()) == report.grand_total
    finally:
        from _offline_providers import unpatch_anthropic

        unpatch_anthropic()
