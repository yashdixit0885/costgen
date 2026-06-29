"""Pricing registry: bundled data + user overrides, with provenance.

Resolution order at lookup is ``override -> bundled`` (FR-014). Every record
carries mandatory ``source`` + ``last_verified`` (Constitution I); records or
overrides missing them are rejected.
"""

from __future__ import annotations

from decimal import Decimal

from .._engine.models import Origin, PricingRecord
from . import _alias


def _key(provider: str, model: str) -> tuple[str, str]:
    return (provider, model)


class PricingRegistry:
    def __init__(self) -> None:
        self._bundled: dict[tuple[str, str], PricingRecord] = {}
        self._overrides: dict[tuple[str, str], PricingRecord] = {}

    # -- population --------------------------------------------------------
    def add_bundled(self, record: PricingRecord) -> None:
        self._bundled[_key(record.provider, record.model)] = record

    def set_override(
        self,
        *,
        provider: str,
        model: str,
        input_price_per_mtok: Decimal | float | str,
        output_price_per_mtok: Decimal | float | str,
        source: str,
        last_verified: str,
        cache_write_multiplier: dict[str, Decimal] | None = None,
        cache_read_multiplier: Decimal | float | str = 0,
        batch_discount: Decimal | float | str = 1,
        currency: str = "USD",
    ) -> PricingRecord:
        record = PricingRecord(
            provider=provider,
            model=model,
            input_price_per_mtok=Decimal(str(input_price_per_mtok)),
            output_price_per_mtok=Decimal(str(output_price_per_mtok)),
            cache_write_multiplier=dict(cache_write_multiplier or {}),
            cache_read_multiplier=Decimal(str(cache_read_multiplier)),
            batch_discount=Decimal(str(batch_discount)),
            currency=currency,
            source=source,  # PricingRecord.__post_init__ enforces non-empty provenance
            last_verified=last_verified,
            origin=Origin.OVERRIDE,
        )
        self._overrides[_key(provider, model)] = record
        return record

    # -- lookup ------------------------------------------------------------
    def lookup(
        self, provider: str, model: str, *, resolve_aliases: bool = True
    ) -> PricingRecord | None:
        """Find a price for (provider, model).

        Exact match wins (override before bundled). Failing that, and if
        ``resolve_aliases`` is set, fall back to base-model candidates so dated
        snapshots and cloud-prefixed/versioned ids (e.g. ``gpt-4o-2024-08-06``,
        ``us.anthropic.claude-opus-4-8``) price against the base model instead of
        being left unpriced. For cloud hosts this is a first-party-list-price
        approximation — register exact rates with ``set_price`` to override it.
        """
        candidates = _alias.candidates(model) if resolve_aliases else [model]
        for cand in candidates:
            key = _key(provider, cand)
            match = self._overrides.get(key) or self._bundled.get(key)
            if match is not None:
                return match
        return None

    def freshness(self, provider: str) -> str | None:
        """Earliest (most stale) ``last_verified`` among that provider's records."""
        dates = [
            r.last_verified
            for store in (self._bundled, self._overrides)
            for (p, _), r in store.items()
            if p == provider
        ]
        return min(dates) if dates else None
