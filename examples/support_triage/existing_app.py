"""A small, realistic "existing" AI app — a customer-support triage assistant.

For every incoming ticket it runs a 3-stage LLM pipeline:

    1. classify urgency   -> OpenAI gpt-4o-mini   (cheap, high volume)
    2. summarize the issue -> Anthropic claude-haiku-4-5 (cheap, cached system prompt)
    3. draft a reply       -> Anthropic claude-opus-4-8  (expensive — the cost driver)

NOTE: this file has **no idea costgen exists**. It is just an app that calls the
OpenAI and Anthropic SDKs the normal way. That is the whole point of the demo —
costgen attaches to these SDK calls without any change here.
"""

from __future__ import annotations

import os

from anthropic import Anthropic
from openai import OpenAI

# A shared system prompt — stable across calls, so it benefits from prompt caching.
SUPPORT_SYSTEM = (
    "You are a senior support engineer for Acme Cloud, a managed Postgres provider. "
    "Be concise, warm, and technically accurate. Never invent account details."
)


def _clients() -> tuple[OpenAI, Anthropic]:
    # In offline demo mode these keys are never used (the SDK calls are mocked).
    return (
        OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "sk-offline-demo")),
        Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "sk-offline-demo")),
    )


def classify_urgency(oai: OpenAI, ticket: dict) -> str:
    resp = oai.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=5,
        messages=[
            {"role": "system", "content": "Classify ticket urgency as low, medium, or high. One word."},
            {"role": "user", "content": ticket["body"]},
        ],
    )
    return resp.choices[0].message.content.strip().lower()


def summarize(ant: Anthropic, ticket: dict) -> str:
    resp = ant.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        system=[{"type": "text", "text": SUPPORT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"Summarize this support ticket in 2 sentences:\n\n{ticket['body']}"}],
    )
    return resp.content[0].text.strip()


def draft_reply(ant: Anthropic, ticket: dict, summary: str, urgency: str) -> str:
    resp = ant.messages.create(
        model="claude-opus-4-8",
        max_tokens=800,
        system=[{"type": "text", "text": SUPPORT_SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Urgency: {urgency}\nInternal summary: {summary}\n\n"
                    f"Write a friendly, helpful reply to this customer:\n\n{ticket['body']}"
                ),
            }
        ],
    )
    return resp.content[0].text.strip()


def process_tickets(tickets: list[dict]) -> list[dict]:
    oai, ant = _clients()
    results = []
    for ticket in tickets:
        urgency = classify_urgency(oai, ticket)
        summary = summarize(ant, ticket)
        reply = draft_reply(ant, ticket, summary, urgency)
        results.append({"id": ticket["id"], "urgency": urgency, "summary": summary, "reply": reply})
    return results


TICKETS = [
    {"id": "T-1001", "body": "My production database has been unreachable for 20 minutes. Getting connection timeouts. This is urgent!"},
    {"id": "T-1002", "body": "How do I rotate the credentials for my read replica without downtime?"},
    {"id": "T-1003", "body": "Billing question: I was charged twice this month for the same plan. Can you check?"},
    {"id": "T-1004", "body": "Feature request: it would be great to have point-in-time restore in the dashboard UI."},
    {"id": "T-1005", "body": "Queries got 5x slower after the last maintenance window. Nothing changed on our side."},
]


def main() -> None:
    print("Acme Cloud — support triage\n" + "-" * 40)
    for r in process_tickets(TICKETS):
        print(f"[{r['id']}] urgency={r['urgency']}")
        print(f"   reply: {r['reply'][:90]}...\n")


if __name__ == "__main__":
    main()
