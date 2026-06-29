"""Callback-adapter capture for LangChain LLMs (both providers, offline).

OpenAI runs the full real SDK via a MockTransport http client (covers the
raw-response path that SDK-level auto-instrumentation misses). Anthropic uses a
real ``Message`` stub on the SDK seam.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

import costgen
from costgen.integrations.langchain import _infer_provider, _usage_from_metadata

pytest.importorskip("langchain_core")


def test_provider_inference():
    assert _infer_provider("claude-opus-4-8") == "anthropic"
    assert _infer_provider("gpt-4o-mini") == "openai"
    assert _infer_provider("o4-mini") == "openai"
    assert _infer_provider("mystery") == "unknown"


def test_usage_from_metadata_subtracts_cache_dimensions():
    # OpenAI-style: input_tokens is total incl cached.
    u = _usage_from_metadata(
        {"input_tokens": 1000, "output_tokens": 50, "input_token_details": {"cache_read": 800}}
    )
    assert u.input_tokens == 200 and u.cache_read_tokens == 800 and u.output_tokens == 50

    # Anthropic-style: input_tokens is total incl cache_read + cache_creation.
    u2 = _usage_from_metadata(
        {
            "input_tokens": 2400,
            "output_tokens": 600,
            "input_token_details": {"cache_read": 900, "cache_creation": 0},
        }
    )
    assert u2.input_tokens == 1500 and u2.cache_read_tokens == 900


def test_callback_captures_langchain_openai_offline():
    pytest.importorskip("langchain_openai")
    import httpx
    from langchain_openai import ChatOpenAI

    def handler(_request):
        return httpx.Response(
            200,
            json={
                "id": "x", "object": "chat.completion", "created": 0, "model": "gpt-4o-mini",
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 50, "total_tokens": 1050,
                          "prompt_tokens_details": {"cached_tokens": 0}},
            },
        )

    costgen.reset()
    cb = costgen.langchain_callback()
    llm = ChatOpenAI(
        model="gpt-4o-mini", api_key="sk-x",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        callbacks=[cb],
    )
    llm.invoke("hi")

    calls = costgen.get_tracker().calls()
    assert len(calls) == 1
    assert calls[0].provider == "openai" and calls[0].model == "gpt-4o-mini"
    # gpt-4o-mini: 1000 input @ $0.15 + 50 output @ $0.60 per MTok
    assert costgen.total() == Decimal("0.00015") + Decimal("0.00003")


def test_callback_captures_langchain_anthropic_offline(monkeypatch):
    pytest.importorskip("langchain_anthropic")
    import anthropic.resources.messages as messages_mod
    from anthropic.types import Message, TextBlock, Usage
    from langchain_anthropic import ChatAnthropic

    def fake_create(self, **kwargs):
        return Message(
            id="m", type="message", role="assistant", model=kwargs.get("model"),
            content=[TextBlock(type="text", text="ok")],
            stop_reason="end_turn", stop_sequence=None,
            usage=Usage(input_tokens=1000, output_tokens=200,
                        cache_creation_input_tokens=0, cache_read_input_tokens=0),
        )

    monkeypatch.setattr(messages_mod.Messages, "create", fake_create)

    costgen.reset()
    llm = ChatAnthropic(model="claude-haiku-4-5", api_key="sk-x", max_tokens=64,
                        callbacks=[costgen.langchain_callback()])
    llm.invoke("hi")

    calls = costgen.get_tracker().calls()
    assert len(calls) == 1 and calls[0].provider == "anthropic"
    # haiku-4-5: 1000 input @ $1 + 200 output @ $5 per MTok = 0.001 + 0.001
    assert costgen.total() == Decimal("0.002")


def test_callback_groups_via_track(monkeypatch):
    pytest.importorskip("langchain_anthropic")
    import anthropic.resources.messages as messages_mod
    from anthropic.types import Message, TextBlock, Usage
    from langchain_anthropic import ChatAnthropic

    monkeypatch.setattr(
        messages_mod.Messages, "create",
        lambda self, **kw: Message(
            id="m", type="message", role="assistant", model=kw.get("model"),
            content=[TextBlock(type="text", text="ok")], stop_reason="end_turn",
            stop_sequence=None,
            usage=Usage(input_tokens=100, output_tokens=10,
                        cache_creation_input_tokens=0, cache_read_input_tokens=0)),
    )

    costgen.reset()
    llm = ChatAnthropic(model="claude-haiku-4-5", api_key="sk-x", max_tokens=8,
                        callbacks=[costgen.langchain_callback()])
    with costgen.track("planner"):
        llm.invoke("plan")

    assert costgen.get_tracker().calls()[0].group == "planner"
