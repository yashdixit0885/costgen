# Phase 1 Data Model: costgen v1

Entities are in-memory dataclasses (no persistence layer). Field names are indicative of the public/export contract; private implementation may add `_`-prefixed fields.

---

## Usage (normalized)

The provider-agnostic token-usage shape the cost engine prices. Produced by `_adapters/normalize.py` from any provider response; consumed by `_engine/calculator.py`.

| Field | Type | Notes |
|---|---|---|
| `input_tokens` | int ≥ 0 | Uncached input tokens (full price). |
| `output_tokens` | int ≥ 0 | Generated tokens. |
| `cache_write_tokens` | int ≥ 0 | Tokens written to cache (Anthropic `cache_creation_input_tokens`). 0 if N/A. |
| `cache_read_tokens` | int ≥ 0 | Tokens served from cache (Anthropic `cache_read_input_tokens`; OpenAI `cached_tokens`). |
| `reasoning_tokens` | int ≥ 0 | Optional passthrough (subset of output for some providers); not double-counted. |
| `cache_ttl` | enum `{none, 5m, 1h}` | Selects the cache-write multiplier where the provider distinguishes TTLs. |

**Validation**: all token counts are non-negative integers. A completely empty/absent usage object → the owning `TrackedCall` is marked `incomplete` (never priced as zero).

---

## PricingRecord

The price basis for one provider/model. Loaded from bundled JSON or a user override.

| Field | Type | Notes |
|---|---|---|
| `provider` | str | e.g. `anthropic`, `openai`. |
| `model` | str | Model identifier as the provider reports it. |
| `input_price_per_mtok` | Decimal | USD per 1M input tokens. |
| `output_price_per_mtok` | Decimal | USD per 1M output tokens. |
| `cache_write_multiplier` | map `{5m,1h} → Decimal` | Multiplier on input price for cache writes (e.g. 1.25 / 2.0). |
| `cache_read_multiplier` | Decimal | Multiplier on input price for cache reads (e.g. 0.1). |
| `batch_discount` | Decimal | Multiplier for batch-API usage (e.g. 0.5); default 1.0. |
| `currency` | str | `USD` (v1). |
| `source` | str | Provenance — URL or reference to the authoritative price. **Required.** |
| `last_verified` | date (ISO-8601) | When the figure was last confirmed. **Required.** |
| `origin` | enum `{bundled, override}` | Whether from package data or a user override. |

**Validation**: `source` and `last_verified` are mandatory (Constitution I) — a record missing either is rejected at load time. Prices are non-negative `Decimal` (not float) for deterministic math (Constitution IV).

**Resolution**: lookup order is `override → bundled`. A model with no record in either → the call is recorded `unpriced`.

---

## TrackedCall

One observed LLM invocation.

| Field | Type | Notes |
|---|---|---|
| `id` | str | Unique per observation (idempotency key for dedupe). |
| `provider` | str | |
| `model` | str | |
| `usage` | Usage \| None | None when usage was unavailable. |
| `measured_cost` | Decimal \| None | Computed from `usage` + `PricingRecord`; None if incomplete/unpriced. |
| `estimated_cost` | Decimal \| None | Set only on estimate calls (Story 3). |
| `completeness` | enum `{complete, partial, incomplete, unpriced}` | Drives reporting flags. |
| `group` | str \| None | User-defined attribution bucket. |
| `tags` | map<str,str> | Optional finer attribution (feature/request/user). |
| `capture_source` | enum `{auto, scoped, explicit}` | Which adapter recorded it. |
| `timestamp` | datetime (UTC) | When recorded. |
| `pricing_origin` | enum `{bundled, override, none}` | Which price basis produced the cost. |

**State**: `completeness` is terminal once set: `complete` (usage present, priced), `partial` (some usage, flagged), `incomplete` (no usable usage), `unpriced` (usage present, no price). A call is **counted exactly once** regardless of how many adapters observed it (dedupe on `id`).

---

## CostGroup

A rolled-up attribution bucket (derived, not stored independently).

| Field | Type | Notes |
|---|---|---|
| `name` | str | Group name (or a sentinel for ungrouped). |
| `total_cost` | Decimal | Sum of member calls' measured cost. |
| `call_count` | int | Member calls. |
| `by_model` | map<str, Decimal> | Cost breakdown within the group. |

**Invariant**: Σ group totals == grand total (FR-018, SC verification).

---

## Estimate

A pre-send cost prediction (Story 3).

| Field | Type | Notes |
|---|---|---|
| `provider` | str | |
| `model` | str | |
| `predicted_input_tokens` | int | From `count_tokens` (Anthropic) or `tiktoken` (OpenAI). |
| `assumed_output_tokens` | int | Caller-supplied / defaulted assumption (reported). |
| `assumptions` | map<str,str> | Human-readable record of what was assumed. |
| `predicted_cost` | Decimal | Priced from the same `PricingRecord`. |
| `kind` | const `"estimate"` | Explicit label so it can never be mistaken for measured. |

---

## CostReport

A point-in-time summary of a run (the report + export payload).

| Field | Type | Notes |
|---|---|---|
| `grand_total` | Decimal | Sum of all measured costs. |
| `measured_total` | Decimal | Measured portion. |
| `estimated_total` | Decimal | Estimated portion (kept separate — never merged into grand total). |
| `by_provider` | map<str, Decimal> | Breakdown; parts sum to grand total. |
| `by_model` | map<str, Decimal> | Breakdown; parts sum to grand total. |
| `by_group` | list<CostGroup> | Breakdown; parts sum to grand total. |
| `incomplete_count` | int | Calls flagged incomplete/partial. |
| `unpriced_count` | int | Calls with no known price. |
| `pricing_freshness` | map<str, date> | Per-provider `last_verified` of the data used. |
| `currency` | str | `USD`. |
| `schema_version` | str | Export schema version (for cross-run diffs). |

**Invariants** (assertable in tests):
- `by_provider` totals, `by_model` totals, and `by_group` totals each sum to `grand_total` (within defined rounding).
- `measured_total` and `estimated_total` are reported separately; `grand_total` reflects measured only.
- Every cost figure is tagged measured vs estimated (Constitution I, SC-003).

---

## Relationships

```
PricingRecord ──prices──▶ Usage ──belongs to──▶ TrackedCall
                                                   │
                              group/tags ──────────┤
                                                   ▼
                                  aggregated into CostGroup / CostReport
Estimate ── priced by ──▶ PricingRecord   (parallel, label = "estimate")
```
