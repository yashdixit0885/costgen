"""T045 — the real-SDK patch targets resolve for the declared version ranges.

Validates that costgen's instrument patch specs point at symbols that actually
exist in the installed openai/anthropic SDKs (the [openai]/[anthropic] extras).
"""

from __future__ import annotations

import pytest

from costgen._adapters import instrument


def _specs_for(provider):
    return [s for s in instrument._SPECS if s.provider == provider]


def test_anthropic_patch_targets_resolve():
    pytest.importorskip("anthropic")
    for spec in _specs_for("anthropic"):
        owner, method = instrument._resolve_owner(spec)
        assert hasattr(owner, method), f"unresolved anthropic seam: {spec.qualname}"


def test_openai_patch_targets_resolve():
    pytest.importorskip("openai")
    for spec in _specs_for("openai"):
        owner, method = instrument._resolve_owner(spec)
        assert hasattr(owner, method), f"unresolved openai seam: {spec.qualname}"


def test_install_uninstall_against_real_sdks_is_clean():
    pytest.importorskip("anthropic")
    pytest.importorskip("openai")
    instrument.install()
    assert instrument.is_installed()
    instrument.uninstall()
    assert not instrument.is_installed()
