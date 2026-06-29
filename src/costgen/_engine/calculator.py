"""Deterministic cost calculator — the engine core.

This module is intentionally generic: it prices a normalized ``Usage`` against a
``PricingRecord`` and contains NO vendor-specific branching. Adding a new vendor
is done by supplying pricing data and a usage normalizer elsewhere — never by
editing this file (Constitution II). Identical inputs always yield identical
``Decimal`` outputs (Constitution IV).
"""

from __future__ import annotations

from decimal import Decimal

from .models import Completeness, PricingRecord, Usage

_PER_MTOK = Decimal(1_000_000)


def price_usage(usage: Usage, record: PricingRecord, *, batch: bool = False) -> Decimal:
    """Return the exact cost of ``usage`` under ``record`` as a ``Decimal``.

    Each priced dimension is independent:
      input  = input_price * input_tokens
      output = output_price * output_tokens
      write  = input_price * write_multiplier[ttl] * cache_write_tokens
      read   = input_price * read_multiplier      * cache_read_tokens
    """
    input_price = record.input_price_per_mtok
    write_mult = record.cache_write_multiplier.get(usage.cache_ttl.value, Decimal(0))

    input_cost = input_price * usage.input_tokens
    output_cost = record.output_price_per_mtok * usage.output_tokens
    write_cost = input_price * write_mult * usage.cache_write_tokens
    read_cost = input_price * record.cache_read_multiplier * usage.cache_read_tokens

    total = (input_cost + output_cost + write_cost + read_cost) / _PER_MTOK
    if batch:
        total = total * record.batch_discount
    return total


def cost_for(
    usage: Usage | None,
    record: PricingRecord | None,
    *,
    batch: bool = False,
) -> tuple[Decimal | None, Completeness]:
    """Resolve cost + completeness for one observation.

    - no usage  -> (None, INCOMPLETE)   — never priced as zero
    - no price  -> (None, UNPRICED)     — surfaced, never dropped
    - otherwise -> (cost, COMPLETE)
    """
    if usage is None:
        return None, Completeness.INCOMPLETE
    if record is None:
        return None, Completeness.UNPRICED
    return price_usage(usage, record, batch=batch), Completeness.COMPLETE
