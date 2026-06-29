"""The shared capture pipeline: normalize -> price -> record.

Every capture adapter (auto-instrument, scoped, explicit) funnels observations
through :func:`observe`, which is wrapped in the non-intrusive guard so it can
never raise into the host application (Constitution III).
"""

from __future__ import annotations

import datetime as _dt
import uuid
from collections.abc import Mapping
from typing import Any

from .._engine import calculator
from .._engine._safe import run_safely
from .._engine.models import CaptureSource, Origin, TrackedCall
from .._engine.tracker import current_scope, get_tracker
from .._pricing import loader as pricing
from . import normalize


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.UTC)


def _observe(
    *,
    provider: str,
    model: str,
    raw_usage: Any,
    capture_source: CaptureSource,
    group: str | None,
    tags: Mapping[str, str] | None,
    call_id: str | None,
    batch: bool,
) -> TrackedCall | None:
    usage = normalize.normalize(provider, raw_usage)
    record = pricing.lookup(provider, model)
    cost, completeness = calculator.cost_for(usage, record, batch=batch)

    # Apply scoped attribution if no explicit group/tags were supplied.
    scope = current_scope()
    if group is None and scope is not None:
        group = scope.group
    resolved_tags = dict(tags or {})
    if scope is not None:
        for k, v in scope.tags.items():
            resolved_tags.setdefault(k, v)

    tracker = get_tracker()
    if record is not None:
        tracker.note_freshness(provider, record.last_verified)

    call = TrackedCall(
        id=call_id or uuid.uuid4().hex,
        provider=provider,
        model=model,
        usage=usage,
        measured_cost=cost,
        completeness=completeness,
        capture_source=capture_source,
        timestamp=_now(),
        group=group,
        tags=resolved_tags,
        pricing_origin=record.origin if record is not None else Origin.NONE,
    )
    return tracker.record(call)


def observe(
    *,
    provider: str,
    model: str,
    raw_usage: Any,
    capture_source: CaptureSource = CaptureSource.AUTO,
    group: str | None = None,
    tags: Mapping[str, str] | None = None,
    call_id: str | None = None,
    batch: bool = False,
) -> TrackedCall | None:
    """Guarded entry point — never raises into the caller."""
    return run_safely(
        _observe,
        provider=provider,
        model=model,
        raw_usage=raw_usage,
        capture_source=capture_source,
        group=group,
        tags=tags,
        call_id=call_id,
        batch=batch,
    )
