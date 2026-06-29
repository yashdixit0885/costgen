"""T016 — provider usage normalization into the engine's Usage."""

from __future__ import annotations

from types import SimpleNamespace

from costgen._adapters import anthropic as an
from costgen._adapters import openai as oa
from costgen._adapters.normalize import detect_provider, normalize


def test_anthropic_dict_usage():
    raw = {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 40,
            "cache_creation_input_tokens": 10,
            "cache_read_input_tokens": 5,
        }
    }
    u = an.to_usage(raw)
    assert (u.input_tokens, u.output_tokens, u.cache_write_tokens, u.cache_read_tokens) == (
        100, 40, 10, 5,
    )
    assert u.cache_ttl.value == "5m"  # write present -> default 5m TTL


def test_anthropic_object_usage():
    resp = SimpleNamespace(usage=SimpleNamespace(input_tokens=7, output_tokens=3))
    u = an.to_usage(resp)
    assert u.input_tokens == 7 and u.output_tokens == 3 and u.cache_write_tokens == 0


def test_anthropic_absent_usage_returns_none():
    assert an.to_usage(None) is None
    assert an.to_usage(SimpleNamespace(usage=SimpleNamespace())) is None


def test_openai_splits_cached_from_input():
    raw = {
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 200,
            "prompt_tokens_details": {"cached_tokens": 800},
            "completion_tokens_details": {"reasoning_tokens": 50},
        }
    }
    u = oa.to_usage(raw)
    assert u.input_tokens == 200  # 1000 - 800 cached
    assert u.cache_read_tokens == 800
    assert u.output_tokens == 200
    assert u.reasoning_tokens == 50


def test_openai_absent_usage_returns_none():
    assert oa.to_usage(None) is None
    assert oa.to_usage({"usage": {}}) is None


def test_openai_unwraps_raw_response_via_parse():
    # Mimics openai's LegacyAPIResponse: no .usage, but a (cached) .parse().
    parsed = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=50))

    class RawResponse:
        usage = None  # raw responses don't expose usage directly

        def parse(self):
            return parsed

    u = oa.to_usage(RawResponse())
    assert u is not None
    assert u.input_tokens == 1000 and u.output_tokens == 50


def test_normalize_dispatch_and_detect():
    assert normalize("anthropic", {"usage": {"input_tokens": 1}}).input_tokens == 1
    assert normalize("nope", {"usage": {}}) is None

    class _Dummy:
        pass

    _Dummy.__module__ = "anthropic.foo"
    assert detect_provider(_Dummy()) == "anthropic"
