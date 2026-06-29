"""Scoped capture: ``track()`` as a context manager AND decorator.

Sets a ``contextvars``-based attribution scope (group + tags) consumed by the
capture pipeline. contextvars propagate into asyncio tasks created within the
block and to code running in the same thread, so concurrent async work is
attributed correctly.
"""

from __future__ import annotations

import contextlib
from collections.abc import Mapping

from .._engine import tracker as _tracker


class track(contextlib.ContextDecorator):
    """Attribute LLM calls made within the block/function to ``group``/``tags``.

    Usage::

        with costgen.track("checkout"):
            ...

        @costgen.track(group="batch", tier="free")
        def handle(...): ...
    """

    def __init__(self, group: str | None = None, **tags: str):
        self.group = group
        self.tags: Mapping[str, str] = tags
        self._token = None

    def __enter__(self) -> track:
        self._token = _tracker.push_scope(self.group, self.tags)
        return self

    def __exit__(self, *exc_info) -> bool:
        if self._token is not None:
            _tracker.reset_scope(self._token)
            self._token = None
        return False
