"""Model-id alias resolution.

Cloud hosts and dated snapshots report model ids that don't match the bundled
price keys, e.g.:

    gpt-4o-2024-08-06                 (OpenAI dated snapshot)
    us.anthropic.claude-opus-4-8      (Bedrock, region + vendor prefix)
    claude-opus-4-5@20251101          (Vertex, @-versioned)

This produces base-model candidates (most-specific first) so pricing lookup can
fall back to the base model when there's no exact price. Exact matches always win
because the original id is the first candidate.
"""

from __future__ import annotations

import re

# Trailing dated snapshot: -20240806 or -2024-08-06
_DATE_SUFFIX = re.compile(r"-(?:\d{8}|\d{4}-\d{2}-\d{2})$")
_VENDOR_PREFIXES = ("anthropic.", "openai.")


def candidates(model: str) -> list[str]:
    """Return [original, ...progressively-normalized base ids], de-duplicated and
    ordered most-specific first."""
    if not model:
        return [model]

    forms: list[str] = []

    def add(value: str) -> None:
        if value and value not in forms:
            forms.append(value)

    add(model)

    # 1) strip an @-version suffix (Vertex): foo@20251101 -> foo
    for f in list(forms):
        if "@" in f:
            add(f.split("@", 1)[0])

    # 2) strip a vendor prefix, incl. an optional region prefix (Bedrock):
    #    us.anthropic.claude-opus-4-8 -> claude-opus-4-8
    for f in list(forms):
        for prefix in _VENDOR_PREFIXES:
            if prefix in f:
                add(f.split(prefix, 1)[1])

    # 3) strip a trailing dated snapshot: gpt-4o-2024-08-06 -> gpt-4o
    for f in list(forms):
        stripped = _DATE_SUFFIX.sub("", f)
        if stripped != f:
            add(stripped)

    return forms
