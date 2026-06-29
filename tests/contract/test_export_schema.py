"""T026 — JSON export conforms to contracts/export-schema.json (structural)."""

from __future__ import annotations

import json
import pathlib

import costgen

_SCHEMA = (
    pathlib.Path(__file__).resolve().parents[2]
    / "specs" / "001-llm-cost-tracking" / "contracts" / "export-schema.json"
)


def test_export_has_required_top_level_keys(fake_provider, tmp_path):
    costgen.reset()
    costgen.record(provider="demo", model="demo-1", group="g",
                   usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}})
    out = tmp_path / "run.json"
    costgen.export(str(out))
    data = json.loads(out.read_text())

    schema = json.loads(_SCHEMA.read_text())
    for key in schema["required"]:
        assert key in data, f"export missing required key {key}"

    # Decimal monetary fields are strings, not floats (exactness).
    assert isinstance(data["grand_total"], str)
    assert isinstance(data["by_provider"]["demo"], str)
    assert data["schema_version"] == "1.0"
    # by_group items have the documented shape
    g = data["by_group"][0]
    assert {"name", "total_cost", "call_count"} <= set(g)
    # per-call detail conforms to the calls item shape
    call = data["calls"][0]
    assert call["completeness"] in {"complete", "partial", "incomplete", "unpriced"}
    assert call["capture_source"] in {"auto", "scoped", "explicit"}
