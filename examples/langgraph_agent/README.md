# Demo: cost-aware LangGraph agent (built with costgen from day one)

A from-scratch **LangGraph** research agent that is cost-aware by design. It shows
the idiomatic way to add costgen to a **framework** app: attach one callback
handler and (optionally) wrap each node in `costgen.track(...)` for per-node cost.

The graph:

```
plan (OpenAI gpt-4o-mini)  ->  research (Anthropic claude-haiku-4-5)  ->  synthesize (Anthropic claude-opus-4-8)
```

## Why a callback (not `install()`)?

LangChain normalizes token usage onto each response, and some integrations
(notably `langchain-openai`) route through the SDK's raw-response path that
SDK-level auto-instrumentation doesn't see. The **callback adapter** reads
LangChain's usage and captures *any* LangChain/LangGraph LLM — OpenAI, Anthropic,
and others — uniformly.

```python
import costgen
cb = costgen.langchain_callback()

plan_llm = ChatOpenAI(model="gpt-4o-mini", callbacks=[cb])
research_llm = ChatAnthropic(model="claude-haiku-4-5", callbacks=[cb])
synth_llm = ChatAnthropic(model="claude-opus-4-8", callbacks=[cb])
```

Per-node attribution — wrap each node's call:

```python
def synthesize(state):
    with costgen.track("synthesize"):
        return {"answer": synth_llm.invoke(...).content}
```

## Run it (no API keys needed)

```bash
pip install "costgen[all]" langgraph langchain-openai langchain-anthropic
python examples/langgraph_agent/run.py
```

Output:

```
By model:
  claude-opus-4-8          $0.028100
  claude-haiku-4-5         $0.003100
  gpt-4o-mini              $0.000093

By group:
  synthesize               $0.028100  (1 calls)   <-- 90% of cost
  research                 $0.003100  (1 calls)
  plan                     $0.000093  (1 calls)
```

**The insight:** the `synthesize` node (Opus) is ~90% of cost. That's where to
act — route easy questions to a cheaper model, cache the system prompt, or only
escalate to Opus when the research is genuinely hard.

## Use real providers

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
python examples/langgraph_agent/run.py --live
```
