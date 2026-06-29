"""T044 — per-captured-call overhead stays within budget (Constitution III, SC-005)."""

from __future__ import annotations

import time

import costgen

# Documented budget: < 1 ms average added work per captured call. We measure the
# observation pipeline directly (excludes the host LLM call itself).
_BUDGET_SECONDS = 0.001


def test_per_call_overhead_within_budget(fake_provider):
    costgen.reset()
    n = 2000
    usage = {"usage": {"input_tokens": 1000, "output_tokens": 500}}

    start = time.perf_counter()
    for _ in range(n):
        costgen.record(provider="demo", model="demo-1", usage=usage)
    elapsed = time.perf_counter() - start

    per_call = elapsed / n
    assert len(costgen.get_tracker().calls()) == n
    assert per_call < _BUDGET_SECONDS, f"overhead {per_call * 1000:.3f} ms/call exceeds budget"
