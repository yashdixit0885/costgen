# Quickstart & Validation Guide: costgen v1

Runnable scenarios that prove each user story end-to-end. Use these as the acceptance walkthrough and as the skeleton for the integration test suite. Implementation lives in `tasks.md` / the implementation phase — this file is a run/validation guide, not the code.

## Prerequisites

- Python 3.11+
- `pip install costgen` (core) — or `pip install "costgen[all]"` for both providers + estimation
- For live-provider scenarios: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`. Offline scenarios use recorded/fake usage objects and need no keys.

Validate the install (SC-010) with both tools:
```bash
python -m pip install costgen && python -c "import costgen; print(costgen.__version__)"
uv pip install costgen && python -c "import costgen; print(costgen.__version__)"
```

---

## Scenario 1 — One-line retrofit measurement (Story 1, P1)

**Goal**: an existing app gets a correct total with zero call-site edits.

```python
import costgen
costgen.install()                 # the only line added to the app

import anthropic                  # existing, unmodified app code below
client = anthropic.Anthropic()
client.messages.create(model="claude-haiku-4-5", max_tokens=64,
                       messages=[{"role": "user", "content": "Hello"}])

costgen.print_report()            # total + breakdown by provider/model
```

**Expected**: a report whose grand total equals the measured cost of the call; the figure is labelled *measured*; no call-site changed.

**Validates**: FR-001, FR-007, FR-009, SC-001, SC-002.

**Framework variant**: run the same with a LangChain/LangGraph chain that uses `langchain-anthropic`; confirm the call is captured with no framework-specific config (FR-002).

---

## Scenario 2 — Breakdown + structured export (Story 2, P1)

```python
import costgen
costgen.install()

with costgen.track(group="search"):
    ...   # calls attributed to "search"
with costgen.track(group="summarize"):
    ...   # calls attributed to "summarize"

costgen.print_report()                       # human-readable, grouped
costgen.export("run.json", format="json")    # machine-readable
costgen.export("run.csv", format="csv")
```

**Expected**:
- Report shows grand total + breakdown by provider, by model, and by group; group totals sum to the grand total.
- `run.json` conforms to `contracts/export-schema.json` and contains the same totals as the report.

**Validates**: FR-017–FR-020, SC-004.

**CI cost-diff** (SC-008, FR-021):
```bash
costgen diff baseline.json run.json    # exits non-zero if cost increased
```

---

## Scenario 3 — Pre-flight estimate (Story 3, P2)

```python
import costgen

est = costgen.estimate(
    provider="anthropic", model="claude-opus-4-8",
    messages=[{"role": "user", "content": "Summarize this 5k-word doc ..."}],
    assumed_output_tokens=500,
)
print(est.kind)                 # "estimate"  — never confused with measured
print(est.predicted_cost, est.assumptions)   # cost + assumed output length reported
```

**Expected**: a predicted cost labelled `estimate`, with the assumed output length reported. Anthropic estimation uses `count_tokens`; OpenAI uses `tiktoken`.

**Validates**: FR-008, FR-009, FR-010, SC-003.

---

## Scenario 4 — Scoped / explicit capture for uncovered paths (Story 4, P2)

```python
import costgen

# Path auto-instrumentation can't reach (e.g. a raw HTTP / LiteLLM call):
resp_usage = {"prompt_tokens": 1200, "completion_tokens": 300,
              "prompt_tokens_details": {"cached_tokens": 800}}
costgen.record(provider="openai", model="gpt-...", usage=resp_usage, group="batch-job")

assert costgen.total() > 0     # included in the grand total
```

**Expected**: the manually-recorded call is attributed to `batch-job` and counted in totals; if `install()` is also active and somehow observes the same call, it is **counted once** (dedupe).

**Validates**: FR-003, FR-004, FR-005, FR-006.

---

## Scenario 5 — Pricing override without a release (FR-014)

```python
import costgen
costgen.set_price(
    provider="anthropic", model="claude-opus-4-8",
    input_price_per_mtok=4.00, output_price_per_mtok=20.00,   # negotiated rate
    source="enterprise-contract-2026", last_verified="2026-06-01",
)
```

**Expected**: subsequent measured costs reflect the override; the report attributes the figure to the override source; omitting `source`/`last_verified` raises `ValueError`.

**Validates**: FR-013, FR-014, FR-015, SC-007, SC-009.

---

## Scenario 6 — Non-intrusiveness & edge cases (Story 1 robustness)

Assert (in tests, not by crashing the app):
- A provider response with **missing usage** → call recorded `incomplete`, **not** priced as zero; app does not error (FR-011).
- An **unknown model** → call recorded `unpriced`, surfaced in the report, not dropped (FR-012).
- An **internal costgen error** (e.g. corrupt pricing file) → logged and swallowed; the host call returns normally (FR-022, SC-005).
- **Double `install()`** and an overlapping `record()` → the call is counted once (FR-005).
- **Concurrent/async** load (many simultaneous calls) → Σ per-call costs == grand total, 100% of runs (FR-023, SC-006).

**Validates**: the Constitution III non-intrusiveness guarantee and the spec edge-case list.

---

## Test mapping

| Scenario | User Story | Primary FRs | Success Criteria |
|---|---|---|---|
| 1 | US1 (P1) | FR-001/002/007/009 | SC-001, SC-002 |
| 2 | US2 (P1) | FR-017–021 | SC-004, SC-008 |
| 3 | US3 (P2) | FR-008/009/010 | SC-003 |
| 4 | US4 (P2) | FR-003/004/005/006 | — |
| 5 | cross-cutting | FR-013/014/015 | SC-007, SC-009 |
| 6 | US1 robustness | FR-011/012/022/023 | SC-005, SC-006 |
| install check | — | FR-025 | SC-010 |
