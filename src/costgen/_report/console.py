"""Human-readable console report (standard library only)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from .._engine.models import CostReport

_Q = Decimal("0.000001")


def _money(value: Decimal) -> str:
    return f"${value.quantize(_Q, rounding=ROUND_HALF_UP)}"


def render(report: CostReport) -> str:
    lines: list[str] = []
    lines.append("costgen — LLM cost report")
    lines.append("=" * 40)
    lines.append(f"Grand total (measured): {_money(report.grand_total)} {report.currency}")
    if report.estimated_total:
        lines.append(f"Estimated (separate):   {_money(report.estimated_total)} {report.currency}")
    lines.append("")

    lines.append("By provider:")
    for name, cost in sorted(report.by_provider.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {name:<18} {_money(cost)}")

    lines.append("")
    lines.append("By model:")
    for name, cost in sorted(report.by_model.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {name:<24} {_money(cost)}")

    if report.by_group:
        lines.append("")
        lines.append("By group:")
        for g in sorted(report.by_group, key=lambda x: -x.total_cost):
            lines.append(f"  {g.name:<24} {_money(g.total_cost)}  ({g.call_count} calls)")

    if report.incomplete_count or report.unpriced_count:
        lines.append("")
        lines.append(
            f"Flags: {report.incomplete_count} incomplete, "
            f"{report.unpriced_count} unpriced (unknown model)"
        )

    if report.pricing_freshness:
        lines.append("")
        lines.append("Pricing last verified:")
        for provider, date in sorted(report.pricing_freshness.items()):
            lines.append(f"  {provider:<18} {date}")

    return "\n".join(lines)
