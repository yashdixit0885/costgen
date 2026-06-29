"""A from-scratch LangGraph research agent, cost-aware by design.

The graph runs three nodes:

    plan (gpt-4o-mini)  ->  research (claude-haiku-4-5)  ->  synthesize (claude-opus-4-8)

This app is built with costgen from day one: a single `costgen.langchain_callback()`
captures the cost of every LLM call the graph makes (across both providers), and
each node wraps its call in `costgen.track(<node>)` so cost is attributed per node.
"""

from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

import costgen


class State(TypedDict, total=False):
    question: str
    plan: str
    findings: str
    answer: str


def build_agent(plan_llm, research_llm, synthesize_llm):
    """Compile the agent graph from three chat models (injected so the same graph
    works offline or live)."""

    def plan(state: State) -> State:
        with costgen.track("plan"):
            resp = plan_llm.invoke(f"Write a 3-step research plan for:\n{state['question']}")
        return {"plan": resp.content}

    def research(state: State) -> State:
        with costgen.track("research"):
            resp = research_llm.invoke(f"Gather concise findings for this plan:\n{state['plan']}")
        return {"findings": resp.content}

    def synthesize(state: State) -> State:
        with costgen.track("synthesize"):
            resp = synthesize_llm.invoke(
                f"Question: {state['question']}\n\nFindings:\n{state['findings']}\n\n"
                "Write a clear, well-structured final answer."
            )
        return {"answer": resp.content}

    graph = StateGraph(State)
    graph.add_node("plan", plan)
    graph.add_node("research", research)
    graph.add_node("synthesize", synthesize)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "research")
    graph.add_edge("research", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()
