"""Anthropic usage parsing.

Anthropic ``usage`` fields:
  input_tokens                  — uncached input (full price)
  output_tokens
  cache_creation_input_tokens   — written to cache (cache-write dimension)
  cache_read_input_tokens       — served from cache (cache-read dimension)

The response does not expose the cache-write TTL, so we default to 5-minute
TTL pricing when a cache write is present.
"""

from __future__ import annotations

from typing import Any

from .._engine.models import CacheTTL, Usage


def _get(obj: Any, name: str, default: int = 0) -> int:
    if obj is None:
        return default
    if isinstance(obj, dict):
        value = obj.get(name, default)
    else:
        value = getattr(obj, name, default)
    return int(value) if value is not None else default


def _extract_usage(raw: Any) -> Any:
    # Accept either a full response (with .usage) or a usage object/dict.
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get("usage", raw)
    return getattr(raw, "usage", raw)


def to_usage(raw: Any) -> Usage | None:
    usage = _extract_usage(raw)
    if usage is None:
        return None
    # An object with no recognizable token fields -> treat as unavailable.
    fields = ("input_tokens", "output_tokens", "cache_creation_input_tokens",
              "cache_read_input_tokens")

    def _has(name: str) -> bool:
        if isinstance(usage, dict):
            return usage.get(name) is not None
        return getattr(usage, name, None) is not None

    if not any(_has(f) for f in fields):
        return None

    cache_write = _get(usage, "cache_creation_input_tokens")
    return Usage(
        input_tokens=_get(usage, "input_tokens"),
        output_tokens=_get(usage, "output_tokens"),
        cache_write_tokens=cache_write,
        cache_read_tokens=_get(usage, "cache_read_input_tokens"),
        cache_ttl=CacheTTL.FIVE_MIN if cache_write else CacheTTL.NONE,
    )
