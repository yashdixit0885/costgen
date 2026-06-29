"""Shared offline helpers so demos run with no API keys / no network.

These make the *real* provider SDKs (and frameworks on top of them) run
end-to-end against canned responses with realistic token usage:

- `openai_offline_http_client(profile)` — an httpx client with a MockTransport
  that returns canned chat-completion JSON; pass it as `http_client=` to the
  OpenAI SDK or `ChatOpenAI`.
- `patch_anthropic(profile)` / `unpatch_anthropic()` — stub the Anthropic SDK's
  `Messages.create` to return a real `anthropic.types.Message`.

`profile(model, kwargs) -> dict` returns the token usage (and reply text) for a
given call, so each demo can shape its own cost story.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

UsageProfile = Callable[[str, dict], dict]


# --------------------------------------------------------------------------- #
# OpenAI — real SDK via MockTransport
# --------------------------------------------------------------------------- #
def openai_offline_http_client(profile: UsageProfile) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content or b"{}")
        model = body.get("model", "gpt-4o-mini")
        spec = profile(model, body)
        prompt = spec.get("input_tokens", 0)
        cached = spec.get("cache_read", 0)
        completion = spec.get("output_tokens", 0)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-offline",
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": spec.get("text", "ok")},
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt,
                    "completion_tokens": completion,
                    "total_tokens": prompt + completion,
                    "prompt_tokens_details": {"cached_tokens": cached},
                },
            },
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


# --------------------------------------------------------------------------- #
# Anthropic — real Message via an SDK seam stub
# --------------------------------------------------------------------------- #
_anthropic_original: Any = None


def patch_anthropic(profile: UsageProfile) -> None:
    global _anthropic_original
    import anthropic.resources.messages as messages_mod
    from anthropic.types import Message, TextBlock, Usage

    if _anthropic_original is None:
        _anthropic_original = messages_mod.Messages.create

    def fake_create(self, **kwargs):
        model = kwargs.get("model", "claude-haiku-4-5")
        spec = profile(model, kwargs)
        # Anthropic input_tokens is the uncached remainder.
        return Message(
            id="msg-offline",
            type="message",
            role="assistant",
            model=model,
            content=[TextBlock(type="text", text=spec.get("text", "ok"))],
            stop_reason="end_turn",
            stop_sequence=None,
            usage=Usage(
                input_tokens=spec.get("input_tokens", 0),
                output_tokens=spec.get("output_tokens", 0),
                cache_creation_input_tokens=spec.get("cache_write", 0),
                cache_read_input_tokens=spec.get("cache_read", 0),
            ),
        )

    messages_mod.Messages.create = fake_create


def unpatch_anthropic() -> None:
    global _anthropic_original
    if _anthropic_original is not None:
        import anthropic.resources.messages as messages_mod

        messages_mod.Messages.create = _anthropic_original
        _anthropic_original = None
