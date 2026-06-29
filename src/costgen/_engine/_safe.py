"""Non-intrusive guard utilities (Constitution III).

Anything that observes/records cost runs inside one of these boundaries so an
internal costgen failure is logged and swallowed — it can never raise into,
block, or crash the host application.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger("costgen")

T = TypeVar("T")


def run_safely(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T | None:
    """Run ``fn`` and return its result; on any exception, log and return None."""
    try:
        return fn(*args, **kwargs)
    except Exception:  # noqa: BLE001 — deliberate catch-all (non-intrusive guarantee)
        logger.warning("costgen: suppressed internal error during cost observation", exc_info=True)
        return None


def safe(fn: Callable[..., T]) -> Callable[..., T | None]:
    """Decorator form of :func:`run_safely` for observation helpers."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> T | None:
        return run_safely(fn, *args, **kwargs)

    return wrapper
