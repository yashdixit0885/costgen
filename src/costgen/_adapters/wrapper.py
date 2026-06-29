"""Explicit capture: ``record()`` a single call, or ``wrap()`` a client proxy.

These are the universal fallback for any path auto-instrumentation does not
reach (LiteLLM, Bedrock/Vertex, raw HTTP, unsupported SDKs).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .._engine.models import CaptureSource, TrackedCall
from . import _pipeline, normalize


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
    """Record one call from a raw provider response/usage object. Counted once
    even if auto-instrumentation also observes it (when a stable ``call_id`` is
    provided)."""
    return _pipeline.observe(
        provider=provider,
        model=model,
        raw_usage=usage,
        capture_source=CaptureSource.EXPLICIT,
        group=group,
        tags=tags,
        call_id=call_id,
        batch=batch,
    )


class _CreateProxy:
    """Wraps a terminal ``create`` callable to observe its result."""

    def __init__(self, fn, provider: str):
        self._fn = fn
        self._provider = provider

    def __call__(self, *args, **kwargs):
        response = self._fn(*args, **kwargs)
        model = kwargs.get("model") or getattr(response, "model", "unknown")
        record(provider=self._provider, model=str(model), usage=response,
               call_id=None)
        return response


class _NamespaceProxy:
    """Recursively proxies attribute access, wrapping any ``create`` callable."""

    def __init__(self, target: Any, provider: str):
        object.__setattr__(self, "_target", target)
        object.__setattr__(self, "_provider", provider)

    def __getattr__(self, name: str):
        attr = getattr(self._target, name)
        if name == "create" and callable(attr):
            return _CreateProxy(attr, self._provider)
        if callable(attr) or isinstance(attr, (str, int, float, bool, type(None))):
            return attr
        return _NamespaceProxy(attr, self._provider)


def wrap(client: Any, *, provider: str | None = None) -> Any:
    """Return a tracking proxy of a provider client. Provider is auto-detected
    from the client's module when not given."""
    provider = provider or normalize.detect_provider(client) or "unknown"
    return _NamespaceProxy(client, provider)
