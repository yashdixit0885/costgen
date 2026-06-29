"""Regression: costgen.install() (no callback) captures langchain-openai calls,
which route through the SDK's with_raw_response path."""

from __future__ import annotations

from decimal import Decimal

import pytest

import costgen

pytest.importorskip("langchain_openai")


def test_install_only_captures_langchain_openai():
    import httpx
    from langchain_openai import ChatOpenAI

    def handler(_request):
        return httpx.Response(
            200,
            json={
                "id": "x", "object": "chat.completion", "created": 0, "model": "gpt-4o-mini",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050},
            },
        )

    costgen.reset()
    costgen.install()  # no langchain callback — pure SDK auto-instrumentation
    try:
        ChatOpenAI(
            model="gpt-4o-mini", api_key="x",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        ).invoke("hi")
    finally:
        costgen.uninstall()

    calls = costgen.get_tracker().calls()
    assert len(calls) == 1
    assert calls[0].completeness.value == "complete"  # usage recovered from the raw response
    # gpt-4o-mini: 1000 input @ $0.15 + 50 output @ $0.60 per MTok
    assert costgen.total() == Decimal("0.00015") + Decimal("0.00003")
