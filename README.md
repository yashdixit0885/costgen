# costgen

[![CI](https://github.com/yashdixit0885/costgen/actions/workflows/ci.yml/badge.svg)](https://github.com/yashdixit0885/costgen/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

**Know what your AI app costs — before the invoice arrives.**

`costgen` is a zero-dependency Python package that tracks and predicts the dollar
cost of your LLM usage. Add **one line** to an existing app and see exactly where
the money goes — by model, by feature, by user — so you can optimize *proactively*
instead of reacting to a surprise bill.

```python
import costgen
costgen.install()          # ← the only line you add

# ... your existing app makes its usual OpenAI / Anthropic calls ...

costgen.print_report()
```

```
costgen — LLM cost report
========================================
Grand total (measured): $0.125189 USD

By model:
  claude-opus-4-8          $0.114750     ← 92% of spend (your optimization target)
  claude-haiku-4-5         $0.010250
  gpt-4o-mini              $0.000189
```

---

## Why costgen?

- **One line, zero refactor.** `costgen.install()` attaches to the OpenAI and
  Anthropic SDKs — no changes to your call sites.
- **Works for new *and* existing apps**, raw-SDK or framework-based
  (LangChain / LangGraph).
- **Measured *and* predicted.** Get exact cost from real token usage, and
  *estimate* cost before you send.
- **Actionable breakdowns.** By provider, model, feature, user — find the 90% you
  can cut.
- **Trustworthy numbers.** Every price carries a source and a `last_verified`
  date; measured and estimated costs are always kept distinct.
- **Lean.** No required runtime dependencies. Provider SDKs live behind optional
  extras.

---

## Install

> Not on PyPI yet — install from source for now:

```bash
pip install "costgen[all] @ git+https://github.com/yashdixit0885/costgen.git"
# or with uv:
uv pip install "costgen[all] @ git+https://github.com/yashdixit0885/costgen.git"
```

Pick only the extras you need:

| Extra | Pulls in | For |
|-------|----------|-----|
| *(none)* | — | the core engine + `track()` / `record()` |
| `costgen[openai]` | `openai`, `tiktoken` | OpenAI auto-instrument + estimation |
| `costgen[anthropic]` | `anthropic` | Anthropic auto-instrument + estimation |
| `costgen[langchain]` | `langchain-core` | LangChain / LangGraph callback |
| `costgen[all]` | all of the above | everything |

---

## Demos — see it on real apps

Every demo runs **offline with no API keys** (realistic canned usage) and takes
`--live` for real providers. Start here:

| Demo | What it teaches | Capture |
|------|-----------------|---------|
| 🎫 **[support_triage](examples/support_triage/)** | One-line retrofit of an **existing** app; per-model breakdown reveals the cost driver | `install()` |
| 🕸️ **[langgraph_agent](examples/langgraph_agent/)** | A **LangGraph** agent built cost-aware from day one; **per-node** + per-model cost across two providers | `langchain_callback()` + `track()` |
| 🌐 **[fastapi_service](examples/fastapi_service/)** | A **FastAPI** service with a `/costs` endpoint and an app-level **budget guard** | `install()` + `track()` |
| 🔀 **[estimate_router](examples/estimate_router/)** | **Pre-flight estimation** routing — downgrade pricey requests *before* sending (~90% saved) | `estimate()` + `install()` |

```bash
python examples/support_triage/run.py --with-costgen
python examples/langgraph_agent/run.py
python examples/fastapi_service/run.py
python examples/estimate_router/run.py
```

See **[examples/README.md](examples/)** for the full index.

---

## How to capture cost

costgen meets your app where it is. Pick the lightest option that fits:

| You have… | Use | Why |
|-----------|-----|-----|
| An app calling the OpenAI/Anthropic SDKs (incl. many frameworks) | **`costgen.install()`** | One line, zero call-site changes |
| A **LangChain / LangGraph** app | **`costgen.langchain_callback()`** | Captures every LLM the chain/graph runs (incl. `langchain-openai`) |
| A region/feature/user to attribute | **`costgen.track(group, **tags)`** | Wrap any block; works with either capture method |
| Something the above can't reach (LiteLLM, Bedrock/Vertex, raw HTTP) | **`costgen.record(...)`** | Explicit, universal fallback |

### Auto-instrument (existing apps)

```python
import costgen
costgen.install()                 # patches the openai + anthropic SDKs
```

### LangChain / LangGraph

```python
import costgen
cb = costgen.langchain_callback()
llm = ChatAnthropic(model="claude-opus-4-8", callbacks=[cb])

# per-node / per-feature cost:
with costgen.track("synthesize"):
    answer = llm.invoke(prompt)
```

### Explicit (any provider / framework)

```python
costgen.record(provider="openai", model="gpt-4o", usage=raw_response.usage, group="batch")
```

---

## What else it does

### Attribute cost to features, requests, or users

```python
with costgen.track("checkout", user="alice"):
    ...   # everything here is attributed to the "checkout" group
```

### Predict cost *before* you send

```python
est = costgen.estimate(provider="anthropic", model="claude-opus-4-8",
                       messages=msgs, assumed_output_tokens=500)
print(est.kind, est.predicted_cost)     # "estimate"  $0.0123
```

Anthropic estimation uses the SDK's native `count_tokens`; OpenAI uses `tiktoken`.
Estimates are always labelled and kept separate from measured cost.

### Report, export, and gate CI on cost

```python
costgen.print_report()                       # human-readable
costgen.export("run.json")                   # structured, diffable
report = costgen.get_report()                # programmatic
total  = costgen.total()                      # running Decimal total
```

```bash
costgen diff baseline.json run.json          # exits non-zero if cost increased
```

### Override pricing without a release

```python
costgen.set_price(provider="anthropic", model="claude-opus-4-8",
                  input_price_per_mtok=4.0, output_price_per_mtok=20.0,
                  source="enterprise-contract", last_verified="2026-06-01")
```

---

## What's auto-captured (and what isn't)

Rule of thumb: **costgen auto-captures any call that goes through the official
`openai` or `anthropic` Python SDK** — including those SDKs' cloud client classes.
It does **not** see calls made through a cloud provider's *native* SDK or raw HTTP.

For LangChain/LangGraph, use `costgen.langchain_callback()`. These paths are **not**
auto-captured — use `costgen.record(...)`:

- LiteLLM and other router/abstraction layers
- **Native** cloud SDKs: `boto3` (Bedrock `invoke_model` / `converse`), Google's
  `google-genai` / Vertex SDK, direct Azure REST calls
- Raw HTTP calls to any provider's REST API

### Using models hosted on Azure, AWS, or GCP

The `openai` and `anthropic` SDKs ship **cloud client classes** that reuse the
*same* methods costgen patches — so `install()` captures them too (verified).
Your credentials are irrelevant: **Azure Key Vault, AWS IAM roles, GCP ADC, and
managed identities make no difference** to whether costgen captures cost — it only
reads token usage from the response.

| Where the model lives | Typical client | Auto-captured? |
|-----------------------|----------------|----------------|
| **Azure** OpenAI / AI Foundry | `openai` → `AzureOpenAI(...)` | ✅ `install()` |
| **AWS** Bedrock (Claude) | `anthropic` → `AnthropicBedrock(...)` | ✅ `install()` |
| **GCP** Vertex AI (Claude) | `anthropic` → `AnthropicVertex(...)` | ✅ `install()` |
| Microsoft Foundry (Claude) | `anthropic` → `AnthropicFoundry(...)` | ✅ `install()` |
| Any of the above via **LangChain** | `AzureChatOpenAI`, `ChatBedrock`, … | ✅ `langchain_callback()` |
| **Native** cloud SDKs (`boto3`, Google GenAI/Vertex SDK, Azure REST) | non-`openai`/`anthropic` | ❌ → `costgen.record(...)` |
| Non-Claude/OpenAI models (Gemini, Llama, Mistral, …) | various | ❌ not a v1 provider |

> **Pricing on cloud — what's automatic vs. what to configure.**
>
> costgen **auto-resolves** dated snapshots and cloud-prefixed / `@`-versioned ids
> to the base model, so they price out of the box at the base-model **list price**:
> `gpt-4o-2024-08-06` → `gpt-4o`, `us.anthropic.claude-opus-4-8` → `claude-opus-4-8`,
> `claude-opus-4-8@20251101` → `claude-opus-4-8`.
>
> Configure prices when you need exactness:
> - **Negotiated / region-specific rates** differ from first-party list prices.
> - **Custom Azure deployment names** (e.g. `my-gpt4o-deploy`) can't be
>   auto-mapped — set a price for them explicitly.
>
> An exact override always wins over alias resolution; effective immediately, no
> reinstall:
>
> ```python
> costgen.set_price(
>     provider="openai", model="my-gpt4o-deploy",        # the id your cloud returns
>     input_price_per_mtok=2.50, output_price_per_mtok=10.00,
>     source="Azure AI Foundry pricing (East US)", last_verified="2026-06-29",
> )
> # or load a file of all your deployment prices:  costgen.load_prices("cloud_prices.json")
> ```
>
> Native cloud SDKs (`boto3`, Google's SDK) and non-Claude/OpenAI models (Gemini,
> Llama, Mistral) aren't auto-captured or priced in v1 — capture them explicitly
> with `costgen.record(provider=..., model=..., usage=...)` plus a `set_price(...)`.

---

## Pricing data & provenance

Bundled prices live in
[`src/costgen/_pricing/data/`](src/costgen/_pricing/data); every record carries a
`source` URL and a `last_verified` date, surfaced in reports. Prices are refreshed
periodically and re-verified before each release. To change a price locally, use
`set_price(...)` / `load_prices(path)` — no reinstall needed.

---

## Supported providers (v1)

| Provider | Models | Measure | Estimate |
|----------|--------|:-------:|:--------:|
| Anthropic | Claude (Opus / Sonnet / Haiku / Fable) | ✅ | ✅ (`count_tokens`) |
| OpenAI | GPT-4o / 4.1 / o-series | ✅ | ✅ (`tiktoken`) |

The cost engine is provider-agnostic — adding a provider means adding pricing data
and a small adapter, never editing the calculation core.

---

## Requirements

- Python **3.11+**
- No required runtime dependencies (provider SDKs are optional extras)

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The project
follows a small set of non-negotiable principles (accuracy + provenance,
provider-agnostic core, non-intrusive capture, test-first with 100% cost-math
coverage).

## License

[MIT](LICENSE)
