# Demo: cost-aware FastAPI service

A small production-style web service that knows its own LLM spend in real time —
exposes it over an endpoint and enforces a budget.

| Endpoint | What it does |
|----------|--------------|
| `POST /chat` | Answer a question with an LLM. Tracked, attributed to the calling user. Returns the per-request cost. |
| `GET /costs` | Live spend: total, budget remaining, by model, by user. |
| `GET /healthz` | Liveness. |

Two things real services want, both from costgen:

1. **Real-time cost visibility** — `/costs` reads costgen's running totals.
2. **A budget guard** — `/chat` returns `429` once spend crosses
   `COSTGEN_BUDGET_USD`, so you stop *before* the invoice, not after.

The whole integration is one line at startup:

```python
import costgen
costgen.install()        # every LLM call in the service is now tracked
```

…plus per-user attribution in the handler:

```python
with costgen.track(req.user, feature="chat"):
    resp = client.messages.create(...)
```

## Run it (no API keys needed)

```bash
pip install "costgen[anthropic]" fastapi uvicorn
python examples/fastapi_service/run.py        # offline mock on http://127.0.0.1:8000
```

In another shell:

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
     -d '{"user":"alice","question":"What is a read replica?"}'
# {"answer":"...","request_cost_usd":"0.0019","total_cost_usd":"0.0019"}

curl -s localhost:8000/costs
# {"total_usd":"0.0019","budget_usd":"0.05","budget_remaining_usd":"0.0481",
#  "by_model":{"claude-haiku-4-5":"0.0019"},"by_user":{"alice":"0.0019"},"calls":1}
```

Keep calling `/chat` and you'll watch `/costs` climb — then `/chat` starts
returning `429 budget reached`. Tune the limit with `COSTGEN_BUDGET_USD`.

## Use real providers

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python examples/fastapi_service/run.py --live
```
