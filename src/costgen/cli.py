"""`costgen` CLI: report / export / diff over saved exports."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

from ._engine.models import CostGroup, CostReport
from ._report import console, export


def _report_from_export(data: dict) -> CostReport:
    def dec(v):
        return Decimal(v) if v is not None else Decimal(0)

    return CostReport(
        grand_total=dec(data.get("grand_total")),
        measured_total=dec(data.get("measured_total")),
        estimated_total=dec(data.get("estimated_total")),
        by_provider={k: dec(v) for k, v in data.get("by_provider", {}).items()},
        by_model={k: dec(v) for k, v in data.get("by_model", {}).items()},
        by_group=[
            CostGroup(
                name=g["name"],
                total_cost=dec(g.get("total_cost")),
                call_count=g.get("call_count", 0),
                by_model={k: dec(v) for k, v in g.get("by_model", {}).items()},
            )
            for g in data.get("by_group", [])
        ],
        incomplete_count=data.get("incomplete_count", 0),
        unpriced_count=data.get("unpriced_count", 0),
        pricing_freshness=data.get("pricing_freshness", {}),
        currency=data.get("currency", "USD"),
        schema_version=data.get("schema_version", "1.0"),
    )


def _load(path: str) -> CostReport:
    with open(path, encoding="utf-8") as fh:
        return _report_from_export(json.load(fh))


def _cmd_report(args) -> int:
    print(console.render(_load(args.input)))
    return 0


def _cmd_export(args) -> int:
    report = _load(args.input)
    if args.format == "csv":
        export.to_csv(report, args.output)
    else:
        export.to_json(report, args.output)
    print(f"wrote {args.output}")
    return 0


def _cmd_diff(args) -> int:
    baseline = _load(args.baseline)
    current = _load(args.current)
    delta = current.grand_total - baseline.grand_total
    print(
        f"baseline={baseline.grand_total} current={current.grand_total} "
        f"delta={delta} {current.currency}"
    )
    # Non-zero exit if cost increased (CI cost-regression gate).
    return 1 if delta > 0 else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="costgen", description="LLM cost reporting")
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="render a saved export as a console report")
    p_report.add_argument("--input", required=True)
    p_report.set_defaults(func=_cmd_report)

    p_export = sub.add_parser("export", help="rewrite an export to json/csv")
    p_export.add_argument("--input", required=True)
    p_export.add_argument("--output", required=True)
    p_export.add_argument("--format", choices=["json", "csv"], default="json")
    p_export.set_defaults(func=_cmd_export)

    p_diff = sub.add_parser("diff", help="exit non-zero if cost increased")
    p_diff.add_argument("baseline")
    p_diff.add_argument("current")
    p_diff.set_defaults(func=_cmd_diff)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
