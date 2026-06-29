# costgen examples

Every demo runs **offline with no API keys** (realistic canned token usage), and
takes `--live` to use real providers. Install costgen with the extras you need.

| Demo | Shows | Capture method |
|------|-------|----------------|
| [support_triage](support_triage/) | One-line retrofit of an **existing** raw-SDK app; per-model breakdown reveals the cost driver | `costgen.install()` |
| [langgraph_agent](langgraph_agent/) | A **LangGraph** agent built cost-aware from day one; **per-node** + per-model cost across two providers | `costgen.langchain_callback()` + `track()` |
| [fastapi_service](fastapi_service/) | A **FastAPI** service with a `/costs` endpoint and an app-level **budget guard** (429 over budget) | `costgen.install()` + `track()` |
| [estimate_router](estimate_router/) | **Pre-flight estimation** routing — downgrade expensive requests *before* sending; ~90% saved on a batch | `costgen.estimate()` + `install()` |

## Which capture method?

- **`costgen.install()`** — one line; patches the OpenAI/Anthropic SDKs. Best for
  apps that call the SDKs directly (incl. many framework apps).
- **`costgen.langchain_callback()`** — for LangChain/LangGraph apps; captures every
  LLM the chain/graph runs (including `langchain-openai`, which routes through the
  SDK's raw-response path that `install()` doesn't see).
- **`costgen.track(group, **tags)`** — wrap any region (a feature, a node, a user)
  to attribute cost to it. Works with either capture method.
- **`costgen.record(...)`** — explicit capture for anything the above can't reach
  (LiteLLM, Bedrock/Vertex, raw HTTP).

## Quick start

```bash
pip install "costgen[all]"
python examples/support_triage/run.py --with-costgen      # one-line retrofit
python examples/langgraph_agent/run.py                    # needs: langgraph langchain-openai langchain-anthropic
python examples/fastapi_service/run.py                    # needs: fastapi uvicorn
python examples/estimate_router/run.py                    # needs: costgen[openai]
```
