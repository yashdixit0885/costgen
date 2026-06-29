# Demo: cost-aware model router (pre-flight estimation)

The "proactive" half of costgen: decide **before** you spend. This router uses
`costgen.estimate()` to predict what a request would cost on a premium model, and
downgrades to a cheaper model when the estimate exceeds a per-request cap.

```
estimate(premium)  ->  over cap?  ->  send on the cheap model
                   ->  under cap? ->  send on the premium model
```

```python
est = costgen.estimate(provider="openai", model="gpt-4o",
                       messages=messages, assumed_output_tokens=150)
model = "gpt-4o-mini" if est.predicted_cost > cap else "gpt-4o"
client.chat.completions.create(model=model, messages=messages, ...)
```

Estimates are clearly labelled (`est.kind == "estimate"`) and never mistaken for
measured cost — OpenAI estimates use `tiktoken`, Anthropic uses the SDK's native
`count_tokens`.

## Run it (no API keys needed)

```bash
pip install "costgen[openai]"
python examples/estimate_router/run.py
```

Output:

```
#1 premium
    premium estimate: $0.00153   chosen: gpt-4o
#4 DOWNGRADED -> cheap
    premium estimate: $0.106565  chosen: gpt-4o-mini   measured: $0.0084
...
If everything ran on gpt-4o (estimated): $0.175
Actual spend with routing:                  $0.018
Saved by routing:                           $0.158 (90%)
```

Short prompts stay on the premium model; the two large documents are downgraded
**before they are ever sent**, cutting spend ~90% on this batch.

## Use real providers

```bash
export OPENAI_API_KEY=sk-...
python examples/estimate_router/run.py --live
```
