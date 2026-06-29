"""Load bundled pricing JSON into a :class:`PricingRegistry` and expose the
process-wide registry plus the public override API."""

from __future__ import annotations

import json
from decimal import Decimal
from importlib import resources

from .._engine.models import Origin, PricingRecord
from .base import PricingRegistry

_DATA_FILES = ("anthropic.json", "openai.json")


def _decimal_map(raw: dict | None) -> dict[str, Decimal]:
    return {k: Decimal(str(v)) for k, v in (raw or {}).items()}


def _load_file(registry: PricingRegistry, filename: str) -> None:
    data = json.loads(resources.files(__package__).joinpath("data", filename).read_text())
    provider = data["provider"]
    source = data["source"]
    last_verified = data["last_verified"]
    default_write = _decimal_map(data.get("cache_write_multiplier"))
    default_read = Decimal(str(data.get("cache_read_multiplier", "0")))
    default_batch = Decimal(str(data.get("batch_discount", "1")))

    for rec in data["records"]:
        registry.add_bundled(
            PricingRecord(
                provider=provider,
                model=rec["model"],
                input_price_per_mtok=Decimal(str(rec["input_price_per_mtok"])),
                output_price_per_mtok=Decimal(str(rec["output_price_per_mtok"])),
                cache_write_multiplier=_decimal_map(rec.get("cache_write_multiplier"))
                or default_write,
                cache_read_multiplier=Decimal(str(rec["cache_read_multiplier"]))
                if "cache_read_multiplier" in rec
                else default_read,
                batch_discount=Decimal(str(rec.get("batch_discount", default_batch))),
                source=rec.get("source", source),
                last_verified=rec.get("last_verified", last_verified),
                origin=Origin.BUNDLED,
            )
        )


def load_bundled() -> PricingRegistry:
    registry = PricingRegistry()
    for filename in _DATA_FILES:
        _load_file(registry, filename)
    return registry


# Process-wide registry.
_registry = load_bundled()


def get_registry() -> PricingRegistry:
    return _registry


def lookup(provider: str, model: str):
    return _registry.lookup(provider, model)


def set_price(
    *,
    provider: str,
    model: str,
    input_price_per_mtok,
    output_price_per_mtok,
    source: str,
    last_verified: str,
    **extra,
):
    """Public override API. ``source`` and ``last_verified`` are required."""
    return _registry.set_override(
        provider=provider,
        model=model,
        input_price_per_mtok=input_price_per_mtok,
        output_price_per_mtok=output_price_per_mtok,
        source=source,
        last_verified=last_verified,
        cache_write_multiplier=extra.get("cache_write_multiplier"),
        cache_read_multiplier=extra.get("cache_read_multiplier", 0),
        batch_discount=extra.get("batch_discount", 1),
        currency=extra.get("currency", "USD"),
    )


def load_prices(path: str) -> None:
    """Load user override prices from a JSON file (same record shape as bundled
    data, but each record must carry ``source`` + ``last_verified``)."""
    data = json.loads(_read(path))
    provider = data["provider"]
    for rec in data["records"]:
        set_price(
            provider=provider,
            model=rec["model"],
            input_price_per_mtok=rec["input_price_per_mtok"],
            output_price_per_mtok=rec["output_price_per_mtok"],
            source=rec.get("source", data.get("source", "")),
            last_verified=rec.get("last_verified", data.get("last_verified", "")),
            cache_write_multiplier=_decimal_map(rec.get("cache_write_multiplier")) or None,
            cache_read_multiplier=rec.get("cache_read_multiplier", 0),
            batch_discount=rec.get("batch_discount", 1),
        )


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()
