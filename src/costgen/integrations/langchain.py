"""LangChain / LangGraph integration: a callback handler that captures the cost
of every LLM call a chain or graph makes.

Why a callback (vs. ``costgen.install()``)? LangChain providers normalize token
usage onto the response message's ``usage_metadata``, and some (e.g.
``langchain-openai``) route through the SDK's raw-response path that the SDK-level
auto-instrumentation does not see. Reading ``usage_metadata`` captures *any*
LangChain LLM — OpenAI, Anthropic, and others — uniformly.

Usage::

    from costgen.integrations.langchain import CostGenCallbackHandler
    handler = CostGenCallbackHandler()
    llm = ChatAnthropic(model="claude-opus-4-8", callbacks=[handler])
    # or per-call: chain.invoke(x, config={"callbacks": [handler]})

`costgen.langchain_callback()` is a convenience that returns one of these.
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from .._adapters import _pipeline
from .._engine.models import CacheTTL, CaptureSource, Usage


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _infer_provider(model: str) -> str:
    m = (model or "").lower()
    if m.startswith("claude") or "anthropic" in m:
        return "anthropic"
    if m.startswith(("gpt", "o1", "o3", "o4", "chatgpt")) or "openai" in m:
        return "openai"
    return "unknown"


def _usage_from_metadata(um: dict) -> Usage:
    """Build the engine's normalized Usage from LangChain ``usage_metadata``.

    LangChain reports ``input_tokens`` as the TOTAL input (including cached and
    cache-creation tokens), so the full-price input is what remains after
    subtracting them. This holds across providers — no vendor branching needed.
    """
    input_details = um.get("input_token_details") or {}
    output_details = um.get("output_token_details") or {}
    cache_read = _int(input_details.get("cache_read"))
    cache_write = _int(input_details.get("cache_creation"))
    total_input = _int(um.get("input_tokens"))
    full_input = max(total_input - cache_read - cache_write, 0)
    return Usage(
        input_tokens=full_input,
        output_tokens=_int(um.get("output_tokens")),
        cache_read_tokens=cache_read,
        cache_write_tokens=cache_write,
        reasoning_tokens=_int(output_details.get("reasoning")),
        cache_ttl=CacheTTL.FIVE_MIN if cache_write else CacheTTL.NONE,
    )


class CostGenCallbackHandler(BaseCallbackHandler):
    """Records the cost of each LLM generation into costgen's tracker.

    Args:
        provider: pin the provider for pricing (else inferred from the model id).
        group: attribute all calls seen by this handler to a cost group. If unset,
            the active ``costgen.track(...)`` scope is used (so you can group per
            graph node).
        tags: extra attribution tags.
    """

    def __init__(
        self,
        *,
        provider: str | None = None,
        group: str | None = None,
        tags: dict[str, str] | None = None,
    ):
        self._provider = provider
        self._group = group
        self._tags = tags or {}

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:  # noqa: D401
        for generations in getattr(response, "generations", []) or []:
            for gen in generations:
                self._record_generation(gen, response)

    def _record_generation(self, gen: Any, response: Any) -> None:
        message = getattr(gen, "message", None)
        um = getattr(message, "usage_metadata", None) if message is not None else None
        if not um:
            return
        model = self._model_of(message, response)
        provider = self._provider or _infer_provider(model)
        _pipeline.observe_usage(
            provider=provider,
            model=model,
            usage=_usage_from_metadata(um),
            capture_source=CaptureSource.AUTO,
            group=self._group,
            tags=self._tags,
        )

    @staticmethod
    def _model_of(message: Any, response: Any) -> str:
        meta = getattr(message, "response_metadata", {}) or {}
        model = meta.get("model_name") or meta.get("model")
        if not model:
            llm_output = getattr(response, "llm_output", None) or {}
            model = llm_output.get("model_name") or llm_output.get("model")
        return str(model or "unknown")
