# Implementation Plan: LLM Cost Tracking & Estimation (costgen v1)

**Branch**: `001-llm-cost-tracking` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-llm-cost-tracking/spec.md`

## Summary

`costgen` is an open-source Python package (PyPI: `costgen`) that AI applications embed to track and predict the dollar cost of their LLM usage. The design centres on one **provider-agnostic cost engine** (deterministic pricing math + attribution + reporting) behind multiple thin **capture adapters**: one-line auto-instrumentation of the `openai`/`anthropic` SDKs, a decorator/context-manager, and an explicit wrapper. It computes *measured* cost from each response's reported token usage and *estimated* cost from pre-flight token counts, keeping the two clearly distinct. v1 supports Anthropic + OpenAI, emits a console/CLI report and a structured JSON/CSV export, and is built to extend to more providers by adding data/adapters only.

## Technical Context

**Language/Version**: Python 3.11+ (per Constitution — older versions are a deliberate, documented exception only)

**Primary Dependencies**: **None required at runtime.** Core engine is pure standard library. Optional extras gate heavy/provider capabilities:
- `costgen[openai]` → instrument the `openai` SDK; `tiktoken` for OpenAI pre-flight estimation
- `costgen[anthropic]` → instrument the `anthropic` SDK; uses its native `messages.count_tokens` for estimation (never `tiktoken` for Claude)
- The provider SDKs are detected at runtime; auto-instrumentation no-ops gracefully when a target SDK is absent.

**Storage**: In-memory accumulation during a run; optional file export (JSON/CSV) via stdlib `json` / `csv`. No database.

**Testing**: `pytest` + `pytest-cov`. Coverage gate **100% on cost-math/calculation modules** (Constitution IV), enforced in CI. Determinism tests (same input → same output). Concurrency/async correctness tests. SDK-version compatibility matrix for the instrumentation adapters.

**Target Platform**: Any environment running CPython 3.11+ (Linux/macOS/Windows); embedded in the host application's process as a library + a `costgen` CLI.

**Project Type**: Single Python library + CLI (`src/` layout).

**Performance Goals**: Per-tracked-call overhead within a documented budget — target **< 1 ms p99 added latency per captured call** and bounded memory (O(number of tracked calls), with optional cap/streaming for very long runs). Verified by a benchmark test.

**Constraints**: NON-INTRUSIVE (Constitution III) — instrumentation MUST never raise into, block, or crash the host app; every internal failure degrades to log-and-continue. Cost math MUST be deterministic (Constitution IV). Attribution MUST stay correct under threads/asyncio.

**Scale/Scope**: v1 = 2 providers (Anthropic, OpenAI), 3 capture adapters, both measure + estimate, console + structured export. Designed for apps making anywhere from a handful to millions of LLM calls per run.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the design satisfies it | Gate |
|---|---|---|
| **I. Measurement Accuracy & Provenance** | Every `PricingRecord` carries a `source` + `last_verified` date; output tags each figure `measured` vs `estimated`; unknown-model/missing-usage calls are surfaced, never silently zero-priced (FR-009, FR-011..FR-015). | ✅ PASS |
| **II. Provider-Agnostic Core** | `engine/calculator.py` has **zero** provider branching — it prices a normalized `Usage` (input/output/cache-write/cache-read dims). Providers add a pricing-data file + a thin `UsageAdapter`. (FR-016) | ✅ PASS |
| **III. Non-Intrusive Integration (NON-NEGOTIABLE)** | All capture paths wrap user-call invocation/observation in guarded boundaries that log-and-continue; a benchmark test asserts the overhead budget. (FR-022, SC-005) | ✅ PASS |
| **IV. Test-First (NON-NEGOTIABLE)** | TDD ordering enforced in tasks; cost-math at 100% coverage; determinism tests. (FR-024, SC-002, SC-006) | ✅ PASS |
| **V. Public API Stability & SemVer** | Public surface is the small, documented `costgen.__init__` API; everything else is a leading-underscore/private module. Releases follow SemVer. | ✅ PASS |
| **VI. Minimal Footprint & Packaging Hygiene** | Zero required runtime deps; `tiktoken`/provider SDKs behind optional extras; clean `pip`/`uv` install; explicit `requires-python`. (FR-025, SC-010) | ✅ PASS |

**Result: PASS — no violations, Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/001-llm-cost-tracking/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (public API + export schema)
│   ├── public-api.md
│   └── export-schema.json
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/costgen/
├── __init__.py              # PUBLIC API: install/uninstall, track, estimate, wrap,
│                            #   report, export, get_tracker, reset; __version__
├── _engine/                 # provider-agnostic cost engine (private)
│   ├── models.py            # Usage, TrackedCall, PricingRecord, CostGroup, CostReport, Estimate
│   ├── calculator.py        # deterministic cost math — 100% coverage target
│   └── tracker.py           # accumulation, grouping/tagging, totals, thread/async-safe store
├── _pricing/                # pricing data + adapters (private)
│   ├── base.py              # PricingProvider protocol + resolution (override > bundled)
│   ├── loader.py            # load bundled JSON + user overrides (env/file/api)
│   └── data/
│       ├── anthropic.json   # bundled prices, each w/ source + last_verified
│       └── openai.json
├── _adapters/               # capture adapters (private)
│   ├── normalize.py         # provider response/usage -> normalized Usage (no core branching)
│   ├── anthropic.py         # anthropic usage parse + SDK patch target
│   ├── openai.py            # openai usage parse + SDK patch target
│   ├── instrument.py        # install()/uninstall() monkeypatch, idempotent, dedupe
│   ├── scoped.py            # track() decorator / context manager (+ group/tag)
│   └── wrapper.py           # explicit wrap()/record()
├── _estimate/               # pre-flight estimation (private)
│   ├── anthropic.py         # uses anthropic messages.count_tokens
│   └── openai.py            # uses tiktoken (extra)
├── _report/
│   ├── console.py           # human-readable summary (stdlib only)
│   └── export.py            # JSON / CSV writers (stdlib json/csv)
└── cli.py                   # `costgen` CLI entry (stdlib argparse)

tests/
├── contract/                # public API shape + export schema conformance
├── integration/             # end-to-end per user story (sample apps, sdk patching)
└── unit/                    # calculator (100%), tracker, normalize, loader, estimate
```

**Structure Decision**: Single-project `src/` layout — `costgen` is a library + CLI, not a web/mobile app. The public API lives only in `costgen/__init__.py`; all implementation is under leading-underscore `_`-prefixed packages to make the SemVer contract surface unambiguous (Constitution V). The `_engine` / `_pricing` / `_adapters` split is the structural expression of Constitution II (provider-agnostic core, pluggable provider data/adapters).

## Complexity Tracking

> No Constitution violations — this section intentionally left empty.
