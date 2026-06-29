"""costgen — add cost visibility to any LLM app in one line.

Public API (the SemVer contract). Everything under ``costgen._*`` is private.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from ._adapters import instrument as _instrument
from ._adapters import wrapper as _wrapper
from ._adapters.scoped import track
from ._engine import calculator as _calculator
from ._engine.models import (
    CostGroup,
    CostReport,
    Estimate,
    PricingRecord,
    TrackedCall,
    Usage,
)
from ._engine.tracker import CostTracker, get_tracker
from ._estimate import anthropic as _est_anthropic
from ._estimate import openai as _est_openai
from ._pricing import loader as _pricing
from ._report import console as _console
from ._report import export as _export

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # capture
    "install",
    "uninstall",
    "track",
    "record",
    "wrap",
    # estimation
    "estimate",
    # integrations
    "langchain_callback",
    # pricing
    "set_price",
    "load_prices",
    # reporting / export
    "report",
    "print_report",
    "export",
    "get_report",
    # tracker lifecycle
    "get_tracker",
    "reset",
    "total",
    # types
    "TrackedCall",
    "Estimate",
    "CostReport",
    "CostGroup",
    "PricingRecord",
    "CostTracker",
    "Usage",
]


# -- Capture ---------------------------------------------------------------
def install(*, providers: list[str] | None = None) -> None:
    """Auto-instrument the supported provider SDKs (one-line retrofit)."""
    _instrument.install(providers=providers)


def uninstall() -> None:
    _instrument.uninstall()


def record(
    *,
    provider: str,
    model: str,
    usage: Any,
    group: str | None = None,
    tags: Mapping[str, str] | None = None,
    call_id: str | None = None,
    batch: bool = False,
) -> TrackedCall | None:
    """Explicitly record one call from a raw provider response/usage object."""
    return _wrapper.record(
        provider=provider,
        model=model,
        usage=usage,
        group=group,
        tags=tags,
        call_id=call_id,
        batch=batch,
    )


def wrap(client: Any, *, provider: str | None = None) -> Any:
    """Return a tracking proxy of a provider client."""
    return _wrapper.wrap(client, provider=provider)


# -- Estimation ------------------------------------------------------------
def estimate(
    *,
    provider: str,
    model: str,
    messages: Any,
    system: Any = None,
    tools: Any = None,
    assumed_output_tokens: int = 0,
    client: Any = None,
) -> Estimate:
    """Return a pre-flight cost ``Estimate`` (labelled, never a measured cost)."""
    if provider == "anthropic":
        n_in = _est_anthropic.count_tokens(model, messages, system, tools, client=client)
        tokenizer = "anthropic.count_tokens"
    elif provider == "openai":
        n_in = _est_openai.count_tokens(model, messages)
        tokenizer = "tiktoken"
    else:
        raise ValueError(f"estimation not supported for provider {provider!r}")

    record_ = _pricing.lookup(provider, model)
    usage = Usage(input_tokens=n_in, output_tokens=assumed_output_tokens)
    cost = _calculator.price_usage(usage, record_) if record_ is not None else None
    return Estimate(
        provider=provider,
        model=model,
        predicted_input_tokens=n_in,
        assumed_output_tokens=assumed_output_tokens,
        predicted_cost=cost,
        assumptions={
            "tokenizer": tokenizer,
            "assumed_output_tokens": str(assumed_output_tokens),
            "note": "output length is assumed; actual measured cost may differ",
        },
    )


# -- Integrations ----------------------------------------------------------
def langchain_callback(
    *,
    provider: str | None = None,
    group: str | None = None,
    tags: Mapping[str, str] | None = None,
):
    """Return a LangChain/LangGraph callback handler that captures LLM cost.

    Attach it via ``callbacks=[...]`` on a chat model or ``config={"callbacks": [...]}``
    on an ``invoke``. Requires the ``costgen[langchain]`` extra.
    """
    from .integrations.langchain import CostGenCallbackHandler

    return CostGenCallbackHandler(provider=provider, group=group, tags=dict(tags or {}))


# -- Pricing overrides -----------------------------------------------------
def set_price(
    *,
    provider: str,
    model: str,
    input_price_per_mtok: Decimal | float | str,
    output_price_per_mtok: Decimal | float | str,
    source: str,
    last_verified: str,
    **extra: Any,
) -> None:
    """Override pricing (requires ``source`` + ``last_verified`` provenance)."""
    _pricing.set_price(
        provider=provider,
        model=model,
        input_price_per_mtok=input_price_per_mtok,
        output_price_per_mtok=output_price_per_mtok,
        source=source,
        last_verified=last_verified,
        **extra,
    )


def load_prices(path: str) -> None:
    _pricing.load_prices(path)


# -- Reporting / export ----------------------------------------------------
def get_report() -> CostReport:
    return get_tracker().get_report()


def report() -> str:
    return _console.render(get_report())


def print_report(file=sys.stdout) -> None:
    print(report(), file=file)


def export(path: str, *, format: str = "json", detailed: bool = True) -> None:  # noqa: A001
    """Write a structured export (``json`` | ``csv``)."""
    rep = get_report()
    if format == "csv":
        _export.to_csv(rep, path)
    else:
        calls = get_tracker().calls() if detailed else None
        _export.to_json(rep, path, calls)


# -- Tracker lifecycle -----------------------------------------------------
def reset() -> None:
    get_tracker().reset()


def total() -> Decimal:
    return get_tracker().total()
