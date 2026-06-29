# Phase 0 Research: costgen v1

Consolidated decisions resolving the Technical Context. Anthropic facts grounded in the bundled `claude-api` reference (cached 2026-06-04); OpenAI facts from the official SDK/usage conventions.

---

## 1. How providers report token usage (measured cost basis)

### Decision
Normalize every provider's usage into a single internal `Usage` shape with four priced dimensions: `input_tokens`, `output_tokens`, `cache_write_tokens`, `cache_read_tokens` (plus an optional `reasoning_tokens` passthrough). The cost engine prices these dimensions and never inspects which provider produced them.

### Rationale
- **Anthropic** (`response.usage`): `input_tokens` (uncached, full price), `output_tokens`, `cache_creation_input_tokens` (cache write — billed ~1.25× for 5-min TTL, ~2× for 1-hour), `cache_read_input_tokens` (cache read — ~0.1×). The *total* prompt size = `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`; `input_tokens` alone is the uncached remainder. Pricing these as separate dimensions is mandatory for correctness — treating cache reads as full-price input would massively overstate cost on cached agents.
- **OpenAI** (`response.usage`): `prompt_tokens`, `completion_tokens`, `total_tokens`, with `prompt_tokens_details.cached_tokens` (discounted cached input) and `completion_tokens_details.reasoning_tokens`. Maps cleanly onto the same four dimensions (cached_tokens → cache_read; OpenAI has no separate cache-write line).
- A four-dimension normalized model covers both providers today and extends to future ones.

### Alternatives considered
- *Price only input+output, ignore cache* — rejected: wrong for any cached workload, and caching is the dominant cost lever (Constitution I: accuracy).
- *Keep provider-native usage objects through the engine* — rejected: forces provider branching into the calculator, violating Constitution II.

---

## 2. Streaming responses

### Decision
Attribute cost only when the stream **completes**; read final usage from the provider's stream-completion accessor. Interrupted streams are recorded as `incomplete`.

### Rationale
- **Anthropic**: usage accrues on the `message_delta` event; the SDK's `stream.get_final_message().usage` exposes the complete record. The auto-instrument adapter wraps the stream helper and reads usage at finalization.
- **OpenAI**: streaming usage requires `stream_options={"include_usage": True}`, delivered in a final usage-only chunk. When the caller doesn't enable it, the call is recorded `incomplete` (usage unavailable) rather than fabricated — satisfying FR-011.

### Alternatives considered
- *Estimate usage from streamed text deltas* — rejected: that is an estimate masquerading as a measurement, violating Constitution I and FR-009.

---

## 3. Pre-flight estimation (estimated cost basis)

### Decision
Per-provider estimation strategy: **Anthropic → native `client.messages.count_tokens(...)`**; **OpenAI → `tiktoken`** (optional extra). Output token count is unknown pre-send, so estimates take an explicit assumed-output-length parameter and report the assumption.

### Rationale
- The bundled reference is explicit: **do not use `tiktoken` for Claude** — it undercounts Claude tokens ~15-20% (more on code/non-English). Anthropic's `count_tokens` endpoint is model-specific and authoritative.
- `tiktoken` is the correct, widely-used tokenizer for OpenAI models and is the standard pre-flight path there.
- Estimates are predictions: input tokens can be counted accurately, output tokens cannot. Reporting the assumed output length (FR-010) keeps the estimate interpretable and honest (Constitution I).

### Alternatives considered
- *One tokenizer for all providers* — rejected: no single tokenizer is accurate across providers; Claude estimation must use Anthropic's counter.
- *Bundle a vendored tokenizer* — rejected: heavy dependency; `tiktoken` stays behind the `[openai]` extra (Constitution VI).

---

## 4. Pricing data, freshness & provenance

### Decision
Ship bundled per-model pricing as JSON data files (one per provider) where **each record carries `source` + `last_verified`**. Resolution order at lookup: **user override → bundled default**. Users supply overrides via a config file path, an env var, or a runtime API — no package release needed for a price change (FR-014).

### Rationale
- Per-MTok input/output prices plus cache-write (5m/1h multipliers or absolute) and cache-read prices, and a Batch-API discount factor, fully describe current Anthropic + OpenAI pricing. Storing them as data (not code) is the Constitution II "add a provider = add data" requirement.
- `last_verified` is surfaced in reports (FR-015, SC-009) so users can judge staleness; stale data still runs (edge case) rather than failing.
- The project documents a refresh cadence (Constitution Additional Constraints).

### Alternatives considered
- *Fetch live prices from a remote endpoint at runtime* — rejected for v1: adds a network dependency and failure mode into a library that must degrade gracefully; revisit as an optional opt-in later.
- *Hardcode prices in Python* — rejected: violates "never silently hardcoded without provenance" (Constitution I).

### Bundled v1 pricing snapshot (per-MTok, USD; `last_verified` set at data-file authoring)
| Provider | Model id | Input | Output | Notes |
|---|---|---|---|---|
| anthropic | claude-opus-4-8 | 5.00 | 25.00 | cache write 1.25×/2×, read 0.1× |
| anthropic | claude-sonnet-4-6 | 3.00 | 15.00 | |
| anthropic | claude-haiku-4-5 | 1.00 | 5.00 | |
| anthropic | claude-fable-5 | 10.00 | 50.00 | |
| openai | (gpt model family) | per official table | per official table | cached-input discount on read dim |

> Implementation task: populate `openai.json` from the official OpenAI pricing table at build time with `last_verified` stamped; Anthropic values above are seeded from the cached reference and re-verified before release.

---

## 5. Auto-instrumentation (zero-touch capture)

### Decision
`costgen.install()` monkeypatches the **method-level** entry points of the `openai` and `anthropic` SDK clients (sync + async; create + stream helpers). It is **idempotent** (double-install is a no-op), reversible via `uninstall()`, and dedupes against the scoped/explicit adapters so a call observed by two mechanisms is counted once (FR-005).

### Rationale
- Patching at the SDK method layer transitively covers framework callers (LangChain/LangGraph/LlamaIndex) that route through these SDKs — the core adoption thesis — without per-framework code.
- A per-call observation carries a unique idempotency marker so overlapping adapters can dedupe.
- Wrapping is defensive: the original method is always invoked; cost observation runs in a guarded boundary that can never propagate an exception into the host call (Constitution III).

### Alternatives considered
- *Patch the shared `httpx` transport* — rejected for v1: catches non-LLM traffic, needs endpoint filtering, noisier; documented as a future option.
- *Framework-native callback adapters (LangChain handler)* — explicitly out of scope for v1 (first fast-follow), per spec.

### Risks / mitigations
- **SDK-version drift** (patch targets move): mitigated by a compatibility test matrix across supported SDK versions and a graceful no-op + warning when a target symbol is absent.

---

## 6. Concurrency & async correctness

### Decision
The accumulation store (`_engine/tracker.py`) is thread-safe (lock-guarded append) and async-safe (no shared mutable state across awaits without protection). Group/tag context uses `contextvars` so scoped attribution is correct across `asyncio` tasks and threads.

### Rationale
- Real AI apps issue many concurrent/async calls; SC-006/FR-023 require no lost or double-counted calls and correct per-group attribution. `contextvars` is the standard Python primitive that propagates correctly across both threads and asyncio tasks.

### Alternatives considered
- *Thread-local storage* — rejected: does not propagate across `asyncio` tasks, breaking grouped attribution in async apps.

---

## 7. Reporting & structured export

### Decision
Console/CLI report rendered with the standard library (no `rich` dependency). Structured export to JSON (primary) and CSV via stdlib `json`/`csv`, against a documented, versioned export schema that is diffable across runs (FR-020, FR-021).

### Rationale
- Zero required deps (Constitution VI). A stable, versioned export schema lets a CI step diff two runs to flag a cost regression (SC-008).

### Alternatives considered
- *`rich`/`click` for output* — rejected as required deps; could be an optional `[pretty]` extra later.

---

## 8. Packaging

### Decision
`src/` layout, `pyproject.toml` (PEP 621), `requires-python = ">=3.11"`, build via `hatchling` (or equivalent PEP 517 backend), published to PyPI as `costgen`. Optional extras: `[openai]`, `[anthropic]`, `[all]`. Installable by both `pip` and `uv`.

### Rationale
- Standard, lean, dual-tool installable (SC-010, Constitution VI). The `src/` layout prevents accidental imports of the uninstalled package during testing.
