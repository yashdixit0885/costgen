---
description: "Task list for costgen v1 — LLM Cost Tracking & Estimation"
---

# Tasks: LLM Cost Tracking & Estimation (costgen v1)

**Input**: Design documents from `specs/001-llm-cost-tracking/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: MANDATORY per Constitution Principle IV (Test-First, NON-NEGOTIABLE). Write tests first, observe them FAIL before implementing, and hold cost-math modules (`_engine/calculator.py`) to **100% coverage**.

**Organization**: Grouped by user story (US1/US2 = P1, US3/US4 = P2) so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no incomplete dependencies)
- **[Story]**: US1–US4 (story-phase tasks only)
- All paths are repo-relative; `src/` layout.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and packaging skeleton.

- [X] T001 Create `src/costgen/` package structure (`_engine/`, `_pricing/data/`, `_adapters/`, `_estimate/`, `_report/`) and `tests/{unit,integration,contract}/` per plan.md project structure
- [X] T002 Author `pyproject.toml` (PEP 621, `hatchling` backend, `requires-python = ">=3.11"`, distribution name `costgen`, zero required runtime deps); declare optional extras with **explicit supported version ranges** (FR-025): `[openai]`→`openai>=…,<…` + `tiktoken>=…`, `[anthropic]`→`anthropic>=…,<…`, `[all]`. The declared ranges are the contract that T045's compatibility matrix tests against.
- [X] T003 [P] Configure `pytest` + `pytest-cov` in `pyproject.toml`/`pytest.ini` with a CI gate enforcing 100% coverage on `src/costgen/_engine/calculator.py`
- [X] T004 [P] Configure `ruff` (lint+format) and a CI workflow in `.github/workflows/ci.yml` running lint, tests, and the coverage gate on pip + uv installs
- [X] T005 [P] Create `src/costgen/__init__.py` exposing the public API names from `contracts/public-api.md` as stubs (raising `NotImplementedError`) plus `__version__`

**Checkpoint**: Package installs (`pip install -e .` / `uv pip install -e .`) and an empty test run passes.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The provider-agnostic cost engine + pricing + normalization that EVERY user story depends on (Constitution II/IV core).

**⚠️ CRITICAL**: No user-story work begins until this phase completes.

- [X] T006 [P] Define core dataclasses in `src/costgen/_engine/models.py` — `Usage`, `PricingRecord`, `TrackedCall`, `CostGroup`, `Estimate`, `CostReport` per data-model.md (Decimal money fields, enums for `completeness`/`capture_source`/`origin`)
- [X] T007 [P] Implement non-intrusive guard utility + logging in `src/costgen/_engine/_safe.py` (a decorator/context that runs observation code, logs-and-swallows any exception — Constitution III)
- [X] T008 [P] [test] Unit tests for the deterministic cost calculator in `tests/unit/test_calculator.py` — input/output/cache-write(5m,1h)/cache-read pricing, batch discount, rounding determinism, unknown-model→unpriced, empty-usage→incomplete; **plus a provider-agnostic guard test asserting `_engine/calculator.py` contains no provider-name branching** (Constitution II, FR-016) (MUST FAIL first)
- [X] T009 Implement deterministic cost calculator in `src/costgen/_engine/calculator.py` — prices a normalized `Usage` against a `PricingRecord` with **zero provider branching**; `Decimal` math; **100% coverage** (depends on T006, T008)
- [X] T010 [P] [test] Unit tests for the tracker in `tests/unit/test_tracker.py` — accumulation, dedupe by call `id`, group/tag attribution, thread- and asyncio-safety, breakdown sums == grand total (MUST FAIL first)
- [X] T011 Implement `CostTracker` in `src/costgen/_engine/tracker.py` — lock-guarded append, dedupe, `contextvars`-based group/tag scope, `by_provider`/`by_model`/`by_group` aggregation, `total()`/`get_report()` (depends on T006, T009, T010)
- [X] T012 [P] [test] Unit tests for pricing load/resolution in `tests/unit/test_pricing.py` — bundled load, override>bundled resolution, mandatory `source`+`last_verified` (missing → `ValueError`), `last_verified` surfaced (MUST FAIL first)
- [X] T013 [P] Create bundled pricing data `src/costgen/_pricing/data/anthropic.json` — opus-4-8 5/25, sonnet-4-6 3/15, haiku-4-5 1/5, fable-5 10/50, cache write 1.25×(5m)/2×(1h), read 0.1×, each record with `source` + `last_verified`
- [X] T014 [P] Create bundled pricing data `src/costgen/_pricing/data/openai.json` — **source the real per-MTok input/output values from the official OpenAI pricing page** for the supported gpt model family (do not leave placeholders), cached-input price on the read dimension, each record with the authoritative `source` URL + the `last_verified` date it was confirmed
- [X] T015 Implement pricing loader + resolution + override API in `src/costgen/_pricing/base.py` and `src/costgen/_pricing/loader.py` — load bundled JSON, `set_price()`/`load_prices()` overrides, lookup `override→bundled`, provenance validation (depends on T006, T012, T013, T014)
- [X] T016 [P] [test] Unit tests for usage normalization in `tests/unit/test_normalize.py` — Anthropic `cache_creation`/`cache_read_input_tokens` and OpenAI `prompt_tokens`+`prompt_tokens_details.cached_tokens` → normalized `Usage`; absent usage → None (MUST FAIL first)
- [X] T017 [P] Implement Anthropic usage parser in `src/costgen/_adapters/anthropic.py` (response/usage → `Usage`) (depends on T006, T016)
- [X] T018 [P] Implement OpenAI usage parser in `src/costgen/_adapters/openai.py` (response/usage → `Usage`, incl. streaming `include_usage` chunk) (depends on T006, T016)

**Checkpoint**: Engine prices any normalized `Usage` deterministically with provenance; foundation ready — user stories can begin.

---

## Phase 3: User Story 1 — One-line retrofit measurement (Priority: P1) 🎯 MVP

**Goal**: `costgen.install()` auto-instruments the openai + anthropic SDKs so an existing app's calls are measured with zero call-site edits; programmatic total + per-model breakdown available.

**Independent Test**: Run a sample app making calls through both SDKs, add only `costgen.install()`, and confirm the grand total equals the summed measured cost and a per-call/per-model breakdown is produced — no call site changed (quickstart Scenario 1).

### Tests for User Story 1 (MANDATORY) ⚠️ — write first, ensure they FAIL

- [X] T019 [P] [US1] Contract test for the capture/measurement public API (`install`/`uninstall`/`total`/`get_report`) in `tests/contract/test_public_api_capture.py`
- [X] T020 [P] [US1] Integration test: patched fake `anthropic` + `openai` clients, calls captured, total == sum of measured costs, zero call-site changes, figures labelled `measured` in `tests/integration/test_us1_autoinstrument.py`
- [X] T021 [P] [US1] Integration test: a LangChain/LangGraph-style caller routing through the anthropic SDK is captured with no framework-specific config in `tests/integration/test_us1_framework.py`
- [X] T022 [P] [US1] Integration test for edge cases in `tests/integration/test_us1_robustness.py`: streaming finalization usage; missing usage → `incomplete` (not zero); unknown model → `unpriced`; double `install()` + overlapping observation counted once; concurrent/async load Σ == grand total; internal error logged-and-swallowed (host call unaffected)

### Implementation for User Story 1

- [X] T023 [US1] Implement auto-instrumentation in `src/costgen/_adapters/instrument.py` — `install(providers=None)`/`uninstall()`: idempotent monkeypatch of anthropic + openai sync/async `create` + stream helpers, original method always invoked inside a `_safe` boundary, unique observation `id` for dedupe, graceful no-op + warning when an SDK/symbol is absent (depends on T007, T017, T018)
- [X] T024 [US1] Implement the capture→cost pipeline wiring (normalize → price via calculator → `record` `TrackedCall(capture_source="auto")` on the tracker) shared by all adapters, in `src/costgen/_adapters/_pipeline.py` (depends on T011, T015, T023)
- [X] T025 [US1] Wire `install`/`uninstall`/`total`/`get_report`/`reset`/`get_tracker` into `src/costgen/__init__.py` (replace stubs) (depends on T023, T024)

**Checkpoint**: US1 fully functional — one-line measurement with a programmatic total + per-model breakdown. **MVP deliverable.**

---

## Phase 4: User Story 2 — See where the money goes & export (Priority: P1)

**Goal**: Human-readable console/CLI report + structured JSON/CSV export, broken down by provider, model, and user-defined group; cross-run cost diff for CI.

**Independent Test**: From a run with grouped captured calls, produce a report and a JSON+CSV export; confirm both carry identical totals and that group totals sum to the grand total; `costgen diff` flags a regression (quickstart Scenario 2).

### Tests for User Story 2 (MANDATORY) ⚠️ — write first, ensure they FAIL

- [X] T026 [P] [US2] Contract test: JSON export conforms to `contracts/export-schema.json` in `tests/contract/test_export_schema.py`
- [X] T027 [P] [US2] Integration test: report shows by-provider / by-model / by-group breakdowns and each set sums to the grand total in `tests/integration/test_us2_report.py`
- [X] T028 [P] [US2] Integration test: JSON & CSV exports carry the same totals as the report; `diff` of two exports detects an increase (exit non-zero) in `tests/integration/test_us2_export_diff.py`

### Implementation for User Story 2

- [X] T029 [US2] Implement `CostReport` builder + `pricing_freshness` (per-provider `last_verified`) and measured/estimated separation in `src/costgen/_engine/tracker.py` (extend) (depends on T011)
- [X] T030 [P] [US2] Implement console renderer in `src/costgen/_report/console.py` (stdlib only) — grand total, by-provider, by-model, by-group, incomplete/unpriced counts, freshness
- [X] T031 [P] [US2] Implement JSON + CSV writers in `src/costgen/_report/export.py` (stdlib `json`/`csv`) against the v1 export schema (Decimal-as-string)
- [X] T032 [US2] Implement CLI in `src/costgen/cli.py` (stdlib `argparse`): `report`, `export`, `diff` subcommands; register `costgen` console_script in `pyproject.toml` (depends on T030, T031)
- [X] T033 [US2] Wire `report`/`print_report`/`export`/`get_report` into `src/costgen/__init__.py` (depends on T029, T030, T031)

**Checkpoint**: US1 + US2 both work — measure, see the breakdown, export, and CI-diff.

---

## Phase 5: User Story 3 — Pre-flight estimate (Priority: P2)

**Goal**: Predict a request's cost before sending, clearly labelled as an estimate, reporting assumed output length.

**Independent Test**: Given a prompt + model, `estimate()` returns a predicted cost labelled `estimate` with reported assumptions; Anthropic uses `count_tokens`, OpenAI uses `tiktoken` (quickstart Scenario 3).

### Tests for User Story 3 (MANDATORY) ⚠️ — write first, ensure they FAIL

- [X] T034 [P] [US3] Contract test: `estimate()` returns an `Estimate` with `kind == "estimate"`, `predicted_cost`, and reported `assumptions` in `tests/contract/test_estimate_api.py`
- [X] T035 [P] [US3] Integration test: Anthropic estimation via `count_tokens` and OpenAI via `tiktoken`; estimate clearly distinct from a later measured actual in `tests/integration/test_us3_estimate.py`

### Implementation for User Story 3

- [X] T036 [P] [US3] Implement Anthropic estimator in `src/costgen/_estimate/anthropic.py` using the anthropic SDK `messages.count_tokens` (graceful error if extra absent)
- [X] T037 [P] [US3] Implement OpenAI estimator in `src/costgen/_estimate/openai.py` using `tiktoken` (graceful error if extra absent)
- [X] T038 [US3] Implement `estimate()` public fn in `src/costgen/__init__.py` — count input tokens per provider, apply `assumed_output_tokens`, price via the calculator, return `Estimate(kind="estimate", assumptions=...)` (depends on T009, T015, T036, T037)

**Checkpoint**: US1–US3 independently functional.

---

## Phase 6: User Story 4 — Scoped & explicit capture (Priority: P2)

**Goal**: `track()` decorator/context-manager (group/tag attribution) and `record()`/`wrap()` explicit capture as the universal fallback for paths auto-instrumentation misses.

**Independent Test**: Wrap a block under a named group, make calls (incl. a path auto-instrument misses), and confirm attribution + inclusion in totals; an explicitly-recorded call also seen by `install()` is counted once (quickstart Scenario 4).

### Tests for User Story 4 (MANDATORY) ⚠️ — write first, ensure they FAIL

- [X] T039 [P] [US4] Integration test: `track()` context-manager + decorator assign group/tags correctly across threads and asyncio tasks in `tests/integration/test_us4_scoped.py`
- [X] T040 [P] [US4] Integration test: `record()` explicit capture counted once even with `install()` active; `wrap()` proxy tracks a client's calls in `tests/integration/test_us4_explicit.py`

### Implementation for User Story 4

- [X] T041 [P] [US4] Implement `track()` decorator/context-manager in `src/costgen/_adapters/scoped.py` setting `contextvar` group/tags consumed by the capture pipeline (depends on T011, T024)
- [X] T042 [P] [US4] Implement `record()` + `wrap()` in `src/costgen/_adapters/wrapper.py` (explicit `TrackedCall(capture_source="explicit")`, dedupe-aware) (depends on T024)
- [X] T043 [US4] Wire `track`/`record`/`wrap` into `src/costgen/__init__.py` (depends on T041, T042)

**Checkpoint**: All four user stories independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T044 [P] Benchmark test asserting the per-captured-call overhead budget (< 1 ms p99) and bounded memory in `tests/unit/test_overhead_budget.py` (Constitution III, SC-005)
- [X] T045 [P] SDK-version compatibility matrix test for the instrument adapters across supported openai/anthropic versions in `tests/integration/test_sdk_compat.py`
- [X] T046 [P] Author `README.md` (install via pip+uv, quickstart, coverage boundary: LiteLLM/Bedrock/Vertex/raw-HTTP not auto-captured) and a `CONTRIBUTING.md` PR template + new-provider-adapter guide (Constitution Dev Workflow)
- [X] T047 [P] `pip` + `uv` clean-install smoke test in CI verifying `import costgen; costgen.__version__` (SC-010)
- [X] T048 Execute all `quickstart.md` scenarios end-to-end as the acceptance walkthrough; record results

---

## Dependencies & Execution Order

### Phase dependencies
- **Setup (P1: T001–T005)** → no deps.
- **Foundational (P2: T006–T018)** → after Setup; **BLOCKS all user stories**.
- **US1 (P3)**, **US2 (P4)**, **US3 (P5)**, **US4 (P6)** → all depend only on Foundational; can proceed in parallel by different developers. US2 reads US1's captured data in practice but is independently testable with synthetic `TrackedCall`s.
- **Polish (P7)** → after the desired stories are complete.

### Within each story
- Tests written and FAILING before implementation (Constitution IV).
- Models → calculator → tracker → adapters/report/estimate.
- `__init__.py` wiring is the last task of each story.

### Parallel opportunities
- Setup: T003, T004, T005 in parallel.
- Foundational: T006/T007 in parallel; test tasks T008/T010/T012/T016 in parallel; data files T013/T014 and parsers T017/T018 in parallel.
- US tests within a story (e.g. T019–T022) in parallel.
- With staffing: US1–US4 in parallel after Foundational.

---

## Parallel Example: Foundational tests

```bash
# Launch the failing unit tests together, then implement against them:
Task: "Unit tests for cost calculator in tests/unit/test_calculator.py"   # T008
Task: "Unit tests for tracker in tests/unit/test_tracker.py"              # T010
Task: "Unit tests for pricing loader in tests/unit/test_pricing.py"       # T012
Task: "Unit tests for usage normalization in tests/unit/test_normalize.py" # T016
```

## Parallel Example: User Story 1 tests

```bash
Task: "Contract test capture API in tests/contract/test_public_api_capture.py"   # T019
Task: "Integration test auto-instrument in tests/integration/test_us1_autoinstrument.py" # T020
Task: "Integration test framework capture in tests/integration/test_us1_framework.py"    # T021
Task: "Integration test robustness/edge cases in tests/integration/test_us1_robustness.py" # T022
```

---

## Implementation Strategy

### MVP First (US1 only)
1. Phase 1 Setup → 2. Phase 2 Foundational (CRITICAL) → 3. Phase 3 US1 → 4. **STOP & VALIDATE** quickstart Scenario 1 → demo one-line measurement.

### Incremental Delivery
Foundational → US1 (MVP: measure) → US2 (see + export) → US3 (estimate) → US4 (scoped/explicit). Each story is an independently testable increment that doesn't break prior stories.

---

## Notes
- `[P]` = different files, no incomplete dependencies.
- `_engine/calculator.py` is the 100%-coverage, deterministic core — keep it provider-agnostic (no `if provider == …`).
- Every `PricingRecord` must carry `source` + `last_verified`; the loader rejects records/overrides without them.
- No capture path may raise into the host app — all observation runs inside the `_safe` boundary (T007).
- Verify tests fail before implementing; commit after each task or logical group.
