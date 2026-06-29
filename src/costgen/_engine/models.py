"""Core data structures for the costgen cost engine.

All monetary values are :class:`decimal.Decimal` for deterministic math
(Constitution IV). Token counts are non-negative integers.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class CacheTTL(str, Enum):
    NONE = "none"
    FIVE_MIN = "5m"
    ONE_HOUR = "1h"


class Completeness(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INCOMPLETE = "incomplete"
    UNPRICED = "unpriced"


class CaptureSource(str, Enum):
    AUTO = "auto"
    SCOPED = "scoped"
    EXPLICIT = "explicit"


class Origin(str, Enum):
    BUNDLED = "bundled"
    OVERRIDE = "override"
    NONE = "none"


def _check_nonneg(name: str, value: int) -> int:
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")
    return value


@dataclass(frozen=True)
class Usage:
    """Provider-agnostic, normalized token usage — the unit the engine prices.

    ``input_tokens`` is the uncached input remainder (full price). Cache
    dimensions are priced separately because cache reads/writes are billed at
    multipliers of the input price.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    reasoning_tokens: int = 0  # subset of output; not double-counted in pricing
    cache_ttl: CacheTTL = CacheTTL.NONE

    def __post_init__(self) -> None:
        _check_nonneg("input_tokens", self.input_tokens)
        _check_nonneg("output_tokens", self.output_tokens)
        _check_nonneg("cache_write_tokens", self.cache_write_tokens)
        _check_nonneg("cache_read_tokens", self.cache_read_tokens)
        _check_nonneg("reasoning_tokens", self.reasoning_tokens)

    @property
    def is_empty(self) -> bool:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_write_tokens
            + self.cache_read_tokens
        ) == 0


@dataclass(frozen=True)
class PricingRecord:
    """Price basis for one provider/model. ``source`` and ``last_verified`` are
    mandatory provenance (Constitution I)."""

    provider: str
    model: str
    input_price_per_mtok: Decimal
    output_price_per_mtok: Decimal
    cache_write_multiplier: dict[str, Decimal] = field(default_factory=dict)
    cache_read_multiplier: Decimal = Decimal(0)
    batch_discount: Decimal = Decimal(1)
    currency: str = "USD"
    source: str = ""
    last_verified: str = ""  # ISO-8601 date
    origin: Origin = Origin.BUNDLED

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError(
                f"PricingRecord for {self.provider}/{self.model} is missing required "
                "'source' provenance"
            )
        if not self.last_verified:
            raise ValueError(
                f"PricingRecord for {self.provider}/{self.model} is missing required "
                "'last_verified' date"
            )
        try:
            _dt.date.fromisoformat(self.last_verified)
        except ValueError as exc:
            raise ValueError(
                f"PricingRecord.last_verified must be an ISO date, got {self.last_verified!r}"
            ) from exc


@dataclass
class TrackedCall:
    """One observed LLM invocation."""

    id: str
    provider: str
    model: str
    usage: Usage | None
    measured_cost: Decimal | None
    completeness: Completeness
    capture_source: CaptureSource
    timestamp: _dt.datetime
    estimated_cost: Decimal | None = None
    group: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    pricing_origin: Origin = Origin.NONE


@dataclass
class CostGroup:
    name: str
    total_cost: Decimal
    call_count: int
    by_model: dict[str, Decimal] = field(default_factory=dict)


@dataclass
class Estimate:
    provider: str
    model: str
    predicted_input_tokens: int
    assumed_output_tokens: int
    predicted_cost: Decimal | None
    assumptions: dict[str, str] = field(default_factory=dict)
    kind: str = "estimate"


@dataclass
class CostReport:
    grand_total: Decimal
    measured_total: Decimal
    estimated_total: Decimal
    by_provider: dict[str, Decimal]
    by_model: dict[str, Decimal]
    by_group: list[CostGroup]
    incomplete_count: int
    unpriced_count: int
    pricing_freshness: dict[str, str]
    currency: str = "USD"
    schema_version: str = "1.0"
