"""A small FastAPI service that is cost-aware in production.

Endpoints:
  POST /chat   — answer a question with an LLM (tracked, attributed per user)
  GET  /costs  — live spend so far: total + breakdown by model and by user
  GET  /healthz

It demonstrates two things real services want:
  1. **Real-time cost visibility** — read costgen's running totals via an endpoint.
  2. **An app-level budget guard** — refuse new work once spend crosses a limit,
     so you never blow past a budget between invoices.

costgen is wired in with one line at startup (`costgen.install()`); the request
handler adds per-user attribution with `costgen.track(...)`.
"""

from __future__ import annotations

import os
from decimal import Decimal

from anthropic import Anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import costgen

# One line makes every LLM call in this service cost-tracked.
costgen.install()

# Refuse new work once spend crosses this budget (USD). Configurable via env.
BUDGET_USD = Decimal(os.environ.get("COSTGEN_BUDGET_USD", "0.05"))

app = FastAPI(title="Acme Assistant (cost-aware)")
_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "sk-offline"))


class ChatRequest(BaseModel):
    user: str
    question: str
    model: str = "claude-haiku-4-5"


class ChatResponse(BaseModel):
    answer: str
    request_cost_usd: str
    total_cost_usd: str


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    # Budget guard: stop before spending more, not after the invoice arrives.
    if costgen.total() >= BUDGET_USD:
        raise HTTPException(
            status_code=429,
            detail=f"LLM budget of ${BUDGET_USD} reached (spent ${costgen.total()}). Try later.",
        )

    before = costgen.total()
    with costgen.track(req.user, feature="chat"):  # attribute spend to the user
        resp = _client.messages.create(
            model=req.model,
            max_tokens=400,
            messages=[{"role": "user", "content": req.question}],
        )
    answer = resp.content[0].text
    request_cost = costgen.total() - before

    return ChatResponse(
        answer=answer,
        request_cost_usd=str(request_cost),
        total_cost_usd=str(costgen.total()),
    )


@app.get("/costs")
def costs() -> dict:
    report = costgen.get_report()
    return {
        "total_usd": str(report.grand_total),
        "budget_usd": str(BUDGET_USD),
        "budget_remaining_usd": str(max(BUDGET_USD - report.grand_total, Decimal(0))),
        "by_model": {k: str(v) for k, v in report.by_model.items()},
        "by_user": {g.name: str(g.total_cost) for g in report.by_group},
        "calls": len(costgen.get_tracker().calls()),
    }
