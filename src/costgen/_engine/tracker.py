"""Accumulation, attribution, and report building.

Thread-safe (lock-guarded) and async-safe (``contextvars`` for scoped
group/tag attribution that propagates correctly across asyncio tasks).
"""

from __future__ import annotations

import contextvars
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from .models import Completeness, CostGroup, CostReport, TrackedCall

_UNGROUPED = "(ungrouped)"


@dataclass
class _Scope:
    group: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


# Scoped attribution set by `track()`. contextvars propagate into asyncio tasks
# and threads that run within a copied context.
_scope: contextvars.ContextVar[_Scope | None] = contextvars.ContextVar(
    "costgen_scope", default=None
)


def current_scope() -> _Scope | None:
    return _scope.get()


def push_scope(group: str | None, tags: Mapping[str, str] | None):
    return _scope.set(_Scope(group=group, tags=dict(tags or {})))


def reset_scope(token) -> None:
    _scope.reset(token)


class CostTracker:
    """In-memory accumulator of :class:`TrackedCall` records."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls: list[TrackedCall] = []
        self._seen_ids: set[str] = set()
        self._freshness: dict[str, str] = {}

    # -- recording ---------------------------------------------------------
    def record(self, call: TrackedCall) -> TrackedCall | None:
        """Record a call exactly once (dedupe by ``id``). Returns the stored
        call, or None if it was a duplicate."""
        with self._lock:
            if call.id in self._seen_ids:
                return None
            self._seen_ids.add(call.id)
            self._calls.append(call)
            return call

    def note_freshness(self, provider: str, last_verified: str) -> None:
        """Record the earliest ``last_verified`` seen per provider (most stale)."""
        with self._lock:
            cur = self._freshness.get(provider)
            if cur is None or last_verified < cur:
                self._freshness[provider] = last_verified

    def reset(self) -> None:
        with self._lock:
            self._calls.clear()
            self._seen_ids.clear()
            self._freshness.clear()

    # -- queries -----------------------------------------------------------
    def total(self) -> Decimal:
        with self._lock:
            return sum((c.measured_cost or Decimal(0) for c in self._calls), Decimal(0))

    def calls(self) -> list[TrackedCall]:
        with self._lock:
            return list(self._calls)

    def get_report(self) -> CostReport:
        with self._lock:
            calls = list(self._calls)
            freshness = dict(self._freshness)

        grand = Decimal(0)
        estimated = Decimal(0)
        by_provider: dict[str, Decimal] = {}
        by_model: dict[str, Decimal] = {}
        groups: dict[str, dict] = {}
        incomplete = 0
        unpriced = 0

        for c in calls:
            if c.estimated_cost is not None:
                estimated += c.estimated_cost
            if c.completeness in (Completeness.INCOMPLETE, Completeness.PARTIAL):
                incomplete += 1
            if c.completeness is Completeness.UNPRICED:
                unpriced += 1

            cost = c.measured_cost
            if cost is None:
                continue
            grand += cost
            by_provider[c.provider] = by_provider.get(c.provider, Decimal(0)) + cost
            by_model[c.model] = by_model.get(c.model, Decimal(0)) + cost

            gname = c.group or _UNGROUPED
            g = groups.setdefault(gname, {"total": Decimal(0), "count": 0, "by_model": {}})
            g["total"] += cost
            g["count"] += 1
            g["by_model"][c.model] = g["by_model"].get(c.model, Decimal(0)) + cost

        by_group = [
            CostGroup(
                name=name,
                total_cost=data["total"],
                call_count=data["count"],
                by_model=dict(data["by_model"]),
            )
            for name, data in groups.items()
        ]

        return CostReport(
            grand_total=grand,
            measured_total=grand,
            estimated_total=estimated,
            by_provider=by_provider,
            by_model=by_model,
            by_group=by_group,
            incomplete_count=incomplete,
            unpriced_count=unpriced,
            pricing_freshness=freshness,
        )


_default_tracker = CostTracker()


def get_tracker() -> CostTracker:
    return _default_tracker
