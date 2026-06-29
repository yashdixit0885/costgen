"""Structured export (JSON canonical, CSV projection) — stdlib only.

Decimals are serialized as strings for exactness. The JSON shape conforms to
contracts/export-schema.json (schema_version 1.0) and is diffable across runs.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from typing import Any

from .._engine.models import CostReport, TrackedCall


def _d(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def report_to_dict(report: CostReport, calls: list[TrackedCall] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": report.schema_version,
        "currency": report.currency,
        "grand_total": _d(report.grand_total),
        "measured_total": _d(report.measured_total),
        "estimated_total": _d(report.estimated_total),
        "incomplete_count": report.incomplete_count,
        "unpriced_count": report.unpriced_count,
        "by_provider": {k: _d(v) for k, v in report.by_provider.items()},
        "by_model": {k: _d(v) for k, v in report.by_model.items()},
        "by_group": [
            {
                "name": g.name,
                "total_cost": _d(g.total_cost),
                "call_count": g.call_count,
                "by_model": {k: _d(v) for k, v in g.by_model.items()},
            }
            for g in report.by_group
        ],
        "pricing_freshness": dict(report.pricing_freshness),
    }
    if calls is not None:
        payload["calls"] = [
            {
                "id": c.id,
                "provider": c.provider,
                "model": c.model,
                "measured_cost": _d(c.measured_cost),
                "estimated_cost": _d(c.estimated_cost),
                "completeness": c.completeness.value,
                "capture_source": c.capture_source.value,
                "group": c.group,
                "tags": dict(c.tags),
                "pricing_origin": c.pricing_origin.value,
                "usage": None
                if c.usage is None
                else {
                    "input_tokens": c.usage.input_tokens,
                    "output_tokens": c.usage.output_tokens,
                    "cache_write_tokens": c.usage.cache_write_tokens,
                    "cache_read_tokens": c.usage.cache_read_tokens,
                    "reasoning_tokens": c.usage.reasoning_tokens,
                },
                "timestamp": c.timestamp.isoformat(),
            }
            for c in calls
        ]
    return payload


def to_json(report: CostReport, path: str, calls: list[TrackedCall] | None = None) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report_to_dict(report, calls), fh, indent=2, sort_keys=True)


def to_csv(report: CostReport, path: str) -> None:
    """Flattened by-model projection of the report."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["dimension", "key", "cost", "currency"])
        writer.writerow(["total", "grand_total", _d(report.grand_total), report.currency])
        for k, v in sorted(report.by_provider.items()):
            writer.writerow(["provider", k, _d(v), report.currency])
        for k, v in sorted(report.by_model.items()):
            writer.writerow(["model", k, _d(v), report.currency])
        for g in report.by_group:
            writer.writerow(["group", g.name, _d(g.total_cost), report.currency])
