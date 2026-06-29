"""OpenAI pre-flight token counting via tiktoken (the [openai] extra)."""

from __future__ import annotations

from typing import Any


def _encoding_for(model: str):
    import tiktoken

    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def _message_text(messages: Any) -> str:
    if isinstance(messages, str):
        return messages
    parts: list[str] = []
    for m in messages or []:
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                text = block.get("text") if isinstance(block, dict) else getattr(block, "text", "")
                if text:
                    parts.append(text)
    return "\n".join(parts)


def count_tokens(model: str, messages: Any, *, encoding: Any = None) -> int:
    enc = encoding or _encoding_for(model)
    # ~4 tokens of per-message framing overhead is a documented approximation.
    overhead = 4 * (len(messages) if isinstance(messages, list) else 1)
    return len(enc.encode(_message_text(messages))) + overhead
