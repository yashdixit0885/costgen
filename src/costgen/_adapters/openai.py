"""OpenAI usage parsing.

OpenAI ``usage`` fields:
  prompt_tokens                              — total input (INCLUDES cached)
  completion_tokens                          — output
  prompt_tokens_details.cached_tokens        — discounted cached input
  completion_tokens_details.reasoning_tokens — subset of completion

Normalization: full-price input = prompt_tokens - cached_tokens; cached_tokens
map to the cache-read dimension (OpenAI has no separate cache-write charge).
"""

from __future__ import annotations

from typing import Any

from .._engine.models import Usage


def _get(obj: Any, name: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _int(value, default: int = 0) -> int:
    return int(value) if value is not None else default


def _extract_usage(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get("usage", raw)
    return getattr(raw, "usage", raw)


def to_usage(raw: Any) -> Usage | None:
    usage = _extract_usage(raw)
    if usage is None:
        return None
    prompt = _get(usage, "prompt_tokens")
    completion = _get(usage, "completion_tokens")
    if prompt is None and completion is None:
        return None

    prompt = _int(prompt)
    completion = _int(completion)

    prompt_details = _get(usage, "prompt_tokens_details")
    cached = _int(_get(prompt_details, "cached_tokens"))
    completion_details = _get(usage, "completion_tokens_details")
    reasoning = _int(_get(completion_details, "reasoning_tokens"))

    uncached_input = max(prompt - cached, 0)
    return Usage(
        input_tokens=uncached_input,
        output_tokens=completion,
        cache_read_tokens=cached,
        reasoning_tokens=reasoning,
    )
