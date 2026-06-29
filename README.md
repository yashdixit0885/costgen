# costgen

**Add cost visibility to any LLM app — new or existing, raw-SDK or framework-based — in one line.**

`costgen` is a zero-dependency Python package that tracks and predicts the dollar
cost of your LLM usage. One provider-agnostic cost engine sits behind thin capture
adapters, so you can retrofit an existing app without touching a single call site.

```bash
pip install costgen          # core (zero runtime deps)
pip install "costgen[all]"   # + openai/anthropic instrumentation + estimation
# or: uv pip install "costgen[all]"
```

## One-line retrofit (measure actual cost)

```python
import costgen
costgen.install()            # the only line you add

# ... your existing, unmodified app code makes its usual LLM calls ...

costgen.print_report()       # total + breakdown by provider / model / group
costgen.export("run.json")   # structured, diffable export
```

`install()` patches the **openai** and **anthropic** SDKs, so calls made by
frameworks that route through those SDKs are captured automatically.

### LangChain / LangGraph

For LangChain/LangGraph apps, attach the callback handler — it captures every LLM
the chain or graph runs (including `langchain-openai`, which uses the SDK's
raw-response path that `install()` doesn't see):

```python
import costgen
cb = costgen.langchain_callback()
llm = ChatAnthropic(model="claude-opus-4-8", callbacks=[cb])
# wrap a graph node for per-node cost:  with costgen.track("synthesize"): ...
```

Requires `pip install "costgen[langchain]"`. See
[examples/langgraph_agent/](examples/langgraph_agent/).

### See it on a real app (no API keys needed)

[`examples/support_triage/`](examples/support_triage/) is a small "existing" app —
a support-triage assistant that classifies, summarizes, and drafts replies across
OpenAI + Anthropic. Add one line and see exactly where the money goes:

```bash
pip install "costgen[all]"
python examples/support_triage/run.py                 # the app today (no cost info)
python examples/support_triage/run.py --with-costgen  # + costgen.install()
```

```
By model:
  claude-opus-4-8          $0.114750     <-- 92% of spend (your optimization target)
  claude-haiku-4-5         $0.010250
  gpt-4o-mini              $0.000189
```

## Attribute cost to features

```python
with costgen.track("checkout", tier="pro"):
    ...   # calls here are attributed to the "checkout" group
```

## Predict cost before sending

```python
est = costgen.estimate(provider="anthropic", model="claude-opus-4-8",
                       messages=msgs, assumed_output_tokens=500)
print(est.kind, est.predicted_cost)   # "estimate"  $...
```

Anthropic estimation uses the SDK's native `count_tokens`; OpenAI uses `tiktoken`.
Estimates are always clearly labelled and kept separate from measured costs.

## Track anything auto-instrumentation can't reach

```python
costgen.record(provider="openai", model="gpt-4o", usage=raw_response_usage, group="batch")
```

## CI cost-regression gate

```bash
costgen diff baseline.json run.json   # exits non-zero if cost increased
```

## v1 coverage boundary

`install()` captures calls that route through the **official openai/anthropic
SDKs** (which covers most framework usage). The following are **not** auto-captured
in v1 — use `track()` / `record()` for them:

- LiteLLM and other router/abstraction layers
- Cloud-gateway SDKs (Amazon Bedrock, Google Vertex)
- Raw HTTP calls to provider REST APIs

## Pricing data & provenance

Bundled prices live in `costgen/_pricing/data/*.json`; every record carries a
`source` and a `last_verified` date, surfaced in reports. Override without a
release:

```python
costgen.set_price(provider="anthropic", model="claude-opus-4-8",
                  input_price_per_mtok=4.0, output_price_per_mtok=20.0,
                  source="enterprise-contract", last_verified="2026-06-01")
```

> Pricing data is refreshed periodically and re-verified before each release.
> Open a PR (see `CONTRIBUTING.md`) to update prices or add a provider.

## License

MIT.
