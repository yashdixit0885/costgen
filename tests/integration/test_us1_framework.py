"""T021 — calls routed through the real anthropic SDK (as a framework would) are
captured with no framework-specific configuration.

Stubs the SDK's Messages.create so no network/keys are needed, then verifies
costgen.install() wraps the real SDK seam and records a measured cost.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

import costgen

anthropic = pytest.importorskip("anthropic")


def test_anthropic_sdk_seam_is_captured():
    import anthropic.resources.messages as messages_mod

    Messages = messages_mod.Messages
    original = Messages.create

    fake_response = type(
        "Resp",
        (),
        {"usage": type("U", (), {"input_tokens": 1000, "output_tokens": 0,
                                 "cache_creation_input_tokens": 0,
                                 "cache_read_input_tokens": 0})(),
         "model": "claude-haiku-4-5"},
    )()

    Messages.create = lambda self, **kwargs: fake_response
    try:
        costgen.reset()
        costgen.install(providers=["anthropic"])
        # A framework (or app) routes a call through the SDK class.
        client = anthropic.Anthropic(api_key="test-not-used")
        client.messages.create(
            model="claude-haiku-4-5", max_tokens=16,
            messages=[{"role": "user", "content": "hi"}],
        )
        # claude-haiku-4-5 input = $1/MTok -> 1000 tokens = $0.001
        assert costgen.total() == Decimal("0.001")
        calls = costgen.get_tracker().calls()
        assert len(calls) == 1 and calls[0].provider == "anthropic"
    finally:
        costgen.uninstall()
        Messages.create = original
