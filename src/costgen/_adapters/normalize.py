"""Normalize provider responses/usage objects into the engine's ``Usage``.

This is the provider-aware boundary. The dispatch table keeps the engine
(``_engine.calculator``) free of any vendor knowledge (Constitution II): adding
a provider = registering a parser here, not editing the calculator.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .._engine.models import Usage
from . import anthropic as _anthropic
from . import openai as _openai

# provider name -> (response/usage -> Usage | None)
_PARSERS: dict[str, Callable[[Any], Usage | None]] = {
    "anthropic": _anthropic.to_usage,
    "openai": _openai.to_usage,
}


def normalize(provider: str, raw: Any) -> Usage | None:
    parser = _PARSERS.get(provider)
    if parser is None:
        return None
    return parser(raw)


def detect_provider(client_or_response: Any) -> str | None:
    """Best-effort provider detection from an object's module (for wrap())."""
    module = getattr(type(client_or_response), "__module__", "") or ""
    root = module.split(".", 1)[0]
    if root in _PARSERS:
        return root
    return None
