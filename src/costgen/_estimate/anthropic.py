"""Anthropic pre-flight token counting via the SDK's native ``count_tokens``.

Never use tiktoken for Claude — it undercounts. ``_make_client`` is a seam so
tests can inject a fake client without network access.
"""

from __future__ import annotations

from typing import Any


def _make_client() -> Any:
    import anthropic  # imported lazily; requires the [anthropic] extra

    return anthropic.Anthropic()


def count_tokens(
    model: str,
    messages: Any,
    system: Any = None,
    tools: Any = None,
    *,
    client: Any = None,
) -> int:
    client = client or _make_client()
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if system is not None:
        kwargs["system"] = system
    if tools is not None:
        kwargs["tools"] = tools
    result = client.messages.count_tokens(**kwargs)
    return int(getattr(result, "input_tokens", result))
