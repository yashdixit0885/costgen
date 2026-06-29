"""Run the LangGraph research agent and report its LLM cost.

    python examples/langgraph_agent/run.py            # offline (no keys)
    python examples/langgraph_agent/run.py --export run.json
    python examples/langgraph_agent/run.py --live     # use real API keys

costgen captures every call the graph makes via one callback handler, and shows
cost per node (plan / research / synthesize) and per model.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import build_agent  # noqa: E402

import costgen  # noqa: E402

QUESTION = "How can we cut our LLM bill ~40% without hurting answer quality?"


def _offline_llms():
    """Real SDKs + frameworks, but driven by canned responses (no keys/network)."""
    from _offline_providers import openai_offline_http_client, patch_anthropic
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI

    def openai_profile(model, body):
        return {"text": "1) scope 2) gather 3) synthesize", "input_tokens": 300, "output_tokens": 80}

    def anthropic_profile(model, kwargs):
        if model.startswith("claude-haiku"):
            return {"text": "Findings: caching + model routing help most.",
                    "input_tokens": 1500, "output_tokens": 300, "cache_read": 1000}
        return {"text": "Final answer: route cheap stages to Haiku, cache the system prompt, "
                        "reserve Opus for the hardest synthesis...",
                "input_tokens": 2000, "output_tokens": 700, "cache_read": 1200}

    patch_anthropic(anthropic_profile)
    cb = costgen.langchain_callback()
    plan = ChatOpenAI(model="gpt-4o-mini", api_key="sk-offline", callbacks=[cb],
                      http_client=openai_offline_http_client(openai_profile))
    research = ChatAnthropic(model="claude-haiku-4-5", api_key="sk-offline", max_tokens=400, callbacks=[cb])
    synth = ChatAnthropic(model="claude-opus-4-8", api_key="sk-offline", max_tokens=800, callbacks=[cb])
    return plan, research, synth


def _live_llms():
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI

    cb = costgen.langchain_callback()
    return (
        ChatOpenAI(model="gpt-4o-mini", callbacks=[cb]),
        ChatAnthropic(model="claude-haiku-4-5", max_tokens=400, callbacks=[cb]),
        ChatAnthropic(model="claude-opus-4-8", max_tokens=800, callbacks=[cb]),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="costgen LangGraph agent demo")
    ap.add_argument("--live", action="store_true", help="use real API keys")
    ap.add_argument("--export", metavar="PATH")
    args = ap.parse_args()

    plan_llm, research_llm, synth_llm = _live_llms() if args.live else _offline_llms()
    app = build_agent(plan_llm, research_llm, synth_llm)

    costgen.reset()
    result = app.invoke({"question": QUESTION})

    print("LangGraph research agent")
    print("-" * 48)
    print(f"Q: {QUESTION}")
    print(f"A: {result['answer'][:120]}...\n")
    costgen.print_report()
    if args.export:
        costgen.export(args.export)
        print(f"\nWrote structured export -> {args.export}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
