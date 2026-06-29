"""One-line auto-instrumentation of the openai/anthropic SDKs.

``install()`` monkeypatches the SDK client methods so existing app code is
tracked with zero call-site changes. It is:
  * idempotent  — calling twice is a no-op (re-install does not double-wrap)
  * reversible  — ``uninstall()`` restores the originals
  * graceful    — a provider whose SDK (or symbol) is absent is skipped + warned
  * non-intrusive — the original method is always invoked; observation runs in a
                    guarded boundary that can never raise into the host call.

Because patching happens at the SDK method layer, calls issued by frameworks
(LangChain/LangGraph/LlamaIndex) that route through these SDKs are captured for
free, with no framework-specific code.
"""

from __future__ import annotations

import functools
import importlib
import inspect
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .._engine._safe import run_safely
from .._engine.models import CaptureSource
from . import _pipeline

logger = logging.getLogger("costgen")

# Marker set on every wrapper so we can detect/restore and avoid double-wrapping.
_MARK = "__costgen_wrapped__"


@dataclass
class PatchSpec:
    provider: str
    module: str  # importable module path
    qualname: str  # attribute chain within the module, e.g. "Messages.create"
    model_from: str = "kwargs"  # where to read the model id: "kwargs" or "response"


# v1 patch targets. Async variants share the same wrapper (it detects coroutines).
_SPECS: list[PatchSpec] = [
    PatchSpec("anthropic", "anthropic.resources.messages", "Messages.create"),
    PatchSpec("anthropic", "anthropic.resources.messages", "AsyncMessages.create"),
    PatchSpec("openai", "openai.resources.chat.completions", "Completions.create", "response"),
    PatchSpec("openai", "openai.resources.chat.completions", "AsyncCompletions.create", "response"),
]

# Records of what we patched, for uninstall: (owner_class, method_name, original).
_patched: list[tuple[Any, str, Callable]] = []
_installed = False


def _resolve_owner(spec: PatchSpec):
    module = importlib.import_module(spec.module)
    obj: Any = module
    parts = spec.qualname.split(".")
    for name in parts[:-1]:
        obj = getattr(obj, name)
    return obj, parts[-1]


def _model_of(spec: PatchSpec, kwargs: dict, response: Any) -> str:
    if spec.model_from == "response":
        model = getattr(response, "model", None)
        if isinstance(response, dict):
            model = response.get("model", model)
        if model:
            return str(model)
    return str(kwargs.get("model", "unknown"))


def _make_wrapper(spec: PatchSpec, original: Callable) -> Callable:
    if inspect.iscoroutinefunction(original):

        @functools.wraps(original)
        async def awrapper(*args: Any, **kwargs: Any):
            response = await original(*args, **kwargs)
            run_safely(_record, spec, kwargs, response)
            return response

        setattr(awrapper, _MARK, original)
        return awrapper

    @functools.wraps(original)
    def wrapper(*args: Any, **kwargs: Any):
        response = original(*args, **kwargs)
        run_safely(_record, spec, kwargs, response)
        return response

    setattr(wrapper, _MARK, original)
    return wrapper


def _record(spec: PatchSpec, kwargs: dict, response: Any) -> None:
    _pipeline.observe(
        provider=spec.provider,
        model=_model_of(spec, kwargs, response),
        raw_usage=response,
        capture_source=CaptureSource.AUTO,
    )


def install(*, providers: list[str] | None = None) -> None:
    """Patch the supported provider SDKs. Idempotent and non-intrusive."""
    global _installed
    wanted = set(providers) if providers else None
    for spec in _SPECS:
        if wanted is not None and spec.provider not in wanted:
            continue
        try:
            owner, method_name = _resolve_owner(spec)
        except (ImportError, AttributeError):
            logger.warning(
                "costgen: %s SDK not available (%s) — skipping auto-instrumentation",
                spec.provider,
                spec.module,
            )
            continue
        current = owner.__dict__.get(method_name, getattr(owner, method_name, None))
        if current is None:
            continue
        if getattr(current, _MARK, None) is not None:
            continue  # already wrapped — idempotent
        wrapper = _make_wrapper(spec, current)
        setattr(owner, method_name, wrapper)
        _patched.append((owner, method_name, current))
    _installed = True


def uninstall() -> None:
    """Restore all patched methods."""
    global _installed
    while _patched:
        owner, method_name, original = _patched.pop()
        setattr(owner, method_name, original)
    _installed = False


def is_installed() -> bool:
    return _installed
