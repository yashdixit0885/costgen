"""T040 — explicit record()/wrap() capture; dedupe with auto-instrumentation."""

from __future__ import annotations

from decimal import Decimal

import costgen
from costgen._engine.models import CaptureSource


def test_record_explicit_counts_in_total(fake_provider):
    costgen.reset()
    call = costgen.record(
        provider="demo", model="demo-1", group="job",
        usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}},
    )
    assert call is not None
    assert call.capture_source is CaptureSource.EXPLICIT
    # 1,000,000 input tokens @ $1.00/MTok = $1.00
    assert costgen.total() == Decimal("1")
    assert costgen.get_tracker().calls()[0].group == "job"


def test_same_call_id_counted_once_even_with_install(fake_sdk):
    # install() is active AND we explicitly record the same logical call id.
    costgen.install()
    first = costgen.record(provider="demo", model="demo-1", call_id="shared-1",
                           usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}})
    second = costgen.record(provider="demo", model="demo-1", call_id="shared-1",
                            usage={"usage": {"input_tokens": 1_000_000, "output_tokens": 0}})
    assert first is not None
    assert second is None  # deduped by id -> counted once
    assert len(costgen.get_tracker().calls()) == 1


def test_wrap_proxy_tracks_create(fake_provider):
    costgen.reset()

    # Mirror real SDK shape: resources are *instances* (not callable), the
    # terminal `create` is a bound method.
    class _Completions:
        def create(self, **kwargs):
            return {"usage": {"input_tokens": 1_000_000, "output_tokens": 0}, "model": "demo-1"}

    class _Chat:
        def __init__(self):
            self.completions = _Completions()

    class FakeClient:
        def __init__(self):
            self.chat = _Chat()

    proxy = costgen.wrap(FakeClient(), provider="demo")
    proxy.chat.completions.create(model="demo-1", messages=[])
    assert costgen.total() == Decimal("1")  # 1M input @ $1/MTok
