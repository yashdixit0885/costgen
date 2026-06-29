# Public API Contract: `costgen` (v1)

This is the **complete** public surface (the SemVer contract per Constitution V). Everything not listed here lives under `costgen._*` private modules and may change without a MAJOR bump. Signatures are indicative; all are importable from the top-level `costgen` package.

```python
import costgen
```

---

## Capture — auto-instrumentation (Story 1, P1)

```python
costgen.install(*, providers: list[str] | None = None) -> None
```
Patches the supported provider SDKs (`openai`, `anthropic`) so all subsequent calls are tracked. **Idempotent** (safe to call twice), **non-intrusive** (never raises into the host app), no-ops with a logged warning for any provider whose SDK is not installed. `providers=None` patches every detected SDK.

```python
costgen.uninstall() -> None
```
Reverses `install()`. Restores original SDK methods.

---

## Capture — scoped (Story 4, P2)

```python
# Context manager
with costgen.track(group: str | None = None, **tags: str):
    ...  # LLM calls inside are attributed to `group`/`tags`

# Decorator form
@costgen.track(group="checkout")
def handle(...): ...
```
Attributes all calls made within the block/function to `group` + `tags`. Works as the universal fallback for paths auto-instrumentation does not reach. Correct under threads and `asyncio` (contextvar-based).

---

## Capture — explicit (Story 4, P2)

```python
costgen.record(
    *, provider: str, model: str, usage: Mapping | object,
    group: str | None = None, tags: Mapping[str, str] | None = None,
) -> TrackedCall
```
Records a single call from a raw provider response/usage object, independent of auto-instrumentation. Returns the resulting `TrackedCall` (counted once even if also seen by `install()`).

```python
costgen.wrap(client: Any) -> Any
```
Returns a thin proxy of a provider client whose calls are tracked explicitly (for callers who prefer wrapping over global patching).

---

## Estimation (Story 3, P2)

```python
costgen.estimate(
    *, provider: str, model: str,
    messages: Any, system: Any | None = None, tools: Any | None = None,
    assumed_output_tokens: int = 0,
) -> Estimate
```
Returns a **pre-flight `Estimate`** (clearly labelled, never a measured cost). Uses Anthropic's `messages.count_tokens` for `provider="anthropic"` and `tiktoken` for `provider="openai"` (requires the matching extra). Reports the `assumed_output_tokens` it used.

---

## Pricing overrides (FR-014)

```python
costgen.set_price(
    *, provider: str, model: str,
    input_price_per_mtok: Decimal | float,
    output_price_per_mtok: Decimal | float,
    source: str, last_verified: str,            # ISO date — provenance required
    **extra,
) -> None

costgen.load_prices(path: str) -> None           # load overrides from a JSON/TOML file
```
Overrides take precedence over bundled prices at lookup time. **`source` and `last_verified` are required** (Constitution I) — a call without them raises `ValueError`.

---

## Reporting & export (Story 2, P1)

```python
costgen.report() -> str                          # human-readable summary string
costgen.print_report(file=sys.stdout) -> None    # render to a stream

costgen.export(path: str, *, format: str = "json") -> None   # "json" | "csv"
costgen.get_report() -> CostReport               # the structured object
```

---

## Tracker lifecycle

```python
costgen.get_tracker() -> CostTracker             # current accumulator
costgen.reset() -> None                          # clear accumulated calls (e.g. per run)
costgen.total() -> Decimal                       # grand total measured cost so far
```

---

## CLI

```text
costgen report  [--input run.json]            # render a saved export as a console report
costgen export  --output run.json [--format json|csv]
costgen diff    <baseline.json> <current.json> # exit non-zero if cost increased (CI gate)
```
The `diff` subcommand enables the CI cost-regression check (SC-008).

---

## Exported types

`TrackedCall`, `Estimate`, `CostReport`, `CostGroup`, `PricingRecord`, `CostTracker`, `Usage` are importable for type hints. `costgen.__version__` exposes the package version.

---

## Guarantees (the contract)

1. **No capture path raises into the host application.** Any internal error is logged and swallowed (Constitution III).
2. **Measured and estimated costs are always distinguishable** in every return value and output (Constitution I).
3. **Each observed call is counted exactly once**, regardless of how many capture mechanisms are active.
4. **Cost math is deterministic** — identical inputs yield identical `Decimal` outputs (Constitution IV).
5. **Every price exposes `source` + `last_verified`** (Constitution I).
6. **Zero required runtime dependencies** for the core; provider/estimation features are optional extras (Constitution VI).
