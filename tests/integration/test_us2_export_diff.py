"""T028 — JSON/CSV export carry the same totals as the report; diff detects a
cost increase (CI cost-regression gate)."""

from __future__ import annotations

import csv
import json
from decimal import Decimal

import costgen
from costgen.cli import main as cli_main


def _emit(model_tokens):
    costgen.reset()
    for tokens in model_tokens:
        costgen.record(
            provider="demo", model="demo-1",
            usage={"usage": {"input_tokens": tokens, "output_tokens": 0}},
        )


def test_json_export_matches_report(fake_provider, tmp_path):
    _emit([1_000_000, 2_000_000])
    report = costgen.get_report()
    out = tmp_path / "run.json"
    costgen.export(str(out), format="json")
    data = json.loads(out.read_text())
    assert Decimal(data["grand_total"]) == report.grand_total
    assert data["schema_version"] == "1.0"
    assert "calls" in data and len(data["calls"]) == 2


def test_csv_export_has_total_row(fake_provider, tmp_path):
    _emit([1_000_000])
    out = tmp_path / "run.csv"
    costgen.export(str(out), format="csv")
    rows = list(csv.reader(out.read_text().splitlines()))
    assert rows[0] == ["dimension", "key", "cost", "currency"]
    total_row = next(r for r in rows if r[1] == "grand_total")
    assert Decimal(total_row[2]) == costgen.get_report().grand_total


def test_diff_exits_nonzero_on_increase(fake_provider, tmp_path):
    base = tmp_path / "base.json"
    cur = tmp_path / "cur.json"
    _emit([1_000_000])
    costgen.export(str(base))
    _emit([5_000_000])
    costgen.export(str(cur))

    assert cli_main(["diff", str(base), str(cur)]) == 1  # increased
    assert cli_main(["diff", str(cur), str(base)]) == 0  # decreased


def test_cli_report_renders(fake_provider, tmp_path, capsys):
    _emit([1_000_000])
    out = tmp_path / "run.json"
    costgen.export(str(out))
    assert cli_main(["report", "--input", str(out)]) == 0
    assert "Grand total" in capsys.readouterr().out
