"""Offline mode: make the OpenAI/Anthropic SDK calls return canned responses with
realistic token usage, so the demo runs with no API keys and no network.

This stubs the SAME SDK methods costgen instruments — so the demo exercises the
real capture path, just without hitting the providers. Token counts are chosen to
tell a realistic cost story (the Opus draft stage dominates).
"""

from __future__ import annotations

from types import SimpleNamespace


def _openai_response(content: str, model: str, prompt: int, completion: int, cached: int = 0):
    return SimpleNamespace(
        model=model,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt,
            completion_tokens=completion,
            prompt_tokens_details=SimpleNamespace(cached_tokens=cached),
            completion_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )


def _anthropic_response(text: str, input_tokens: int, output_tokens: int, cache_read: int = 0):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=cache_read,
        ),
    )


_SUMMARY = "Customer is blocked by a production issue and needs a clear next step. Tone should be reassuring and specific."
_DRAFT = (
    "Hi there — thanks for reaching out, and sorry for the trouble. I've looked into this and "
    "here's what I'd suggest as the immediate next step... (full reply omitted in demo)."
)


_originals: dict = {}


def disable() -> None:
    """Restore the real SDK create methods (used by tests for isolation)."""
    import anthropic.resources.messages as messages_mod
    import openai.resources.chat.completions as completions_mod

    if "openai" in _originals:
        completions_mod.Completions.create = _originals.pop("openai")
    if "anthropic" in _originals:
        messages_mod.Messages.create = _originals.pop("anthropic")


def enable() -> None:
    """Patch the provider SDK create methods with offline stubs."""
    import anthropic.resources.messages as messages_mod
    import openai.resources.chat.completions as completions_mod

    _originals.setdefault("openai", completions_mod.Completions.create)
    _originals.setdefault("anthropic", messages_mod.Messages.create)

    def fake_openai_create(self, **kwargs):
        # Urgency classification — tiny prompt, one-word answer.
        return _openai_response("medium", kwargs.get("model", "gpt-4o-mini"),
                                prompt=240, completion=3)

    def fake_anthropic_create(self, **kwargs):
        model = kwargs.get("model", "")
        if model.startswith("claude-haiku"):
            # Summarize — cheap model, shared system prompt served from cache.
            return _anthropic_response(_SUMMARY, input_tokens=1200, output_tokens=150,
                                       cache_read=1000)
        # Draft reply — expensive Opus call; the cost driver.
        return _anthropic_response(_DRAFT, input_tokens=1500, output_tokens=600,
                                   cache_read=900)

    completions_mod.Completions.create = fake_openai_create
    messages_mod.Messages.create = fake_anthropic_create
