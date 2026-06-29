"""Run the cost-aware estimate router over a batch of prompts.

    python examples/estimate_router/run.py            # offline (no keys)
    python examples/estimate_router/run.py --live     # real OPENAI_API_KEY

Short prompts stay on the premium model; long/expensive ones are downgraded
before they are ever sent. The summary shows estimated vs. measured and the
savings from routing.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from router import CHEAP, PREMIUM, route_and_answer  # noqa: E402

import costgen  # noqa: E402

PROMPTS = [
    "Define idempotency in one sentence.",
    "What port does Postgres use by default?",
    "List three index types in Postgres.",
    (
        "Here is a long incident postmortem; summarize root cause, remediation, and "
        "preventative actions in detail.\n\n" + "context line of the incident report. " * 6000
    ),
    (
        "Review this large migration plan and flag every risk with mitigations, step "
        "by step, citing each phase.\n\n" + "migration phase detail line. " * 5000
    ),
]

PER_REQUEST_CAP = Decimal("0.004")  # downgrade requests estimated above $0.004


def _offline_client():
    from _offline_providers import openai_offline_http_client
    from openai import OpenAI

    def profile(model, body):
        text = " ".join(
            m.get("content", "") for m in body.get("messages", []) if isinstance(m.get("content"), str)
        )
        prompt_tokens = max(len(text) // 4, 1)  # rough offline approximation
        return {"text": "answer", "input_tokens": prompt_tokens, "output_tokens": 120}

    return OpenAI(api_key="sk-offline", http_client=openai_offline_http_client(profile))


def _live_client():
    from openai import OpenAI

    return OpenAI()


def main() -> int:
    ap = argparse.ArgumentParser(description="costgen estimate-router demo")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--export", metavar="PATH")
    args = ap.parse_args()

    client = _live_client() if args.live else _offline_client()
    costgen.install()  # measure what we actually send
    costgen.reset()

    print("Cost-aware estimate router")
    print("-" * 60)
    print(f"Premium={PREMIUM}  Cheap={CHEAP}  cap=${PER_REQUEST_CAP}/request\n")

    premium_estimate_total = Decimal(0)
    for i, prompt in enumerate(PROMPTS, 1):
        chosen, est, measured = route_and_answer(client, prompt, per_request_cap_usd=PER_REQUEST_CAP)
        premium_estimate_total += est.predicted_cost or Decimal(0)
        flag = "premium" if chosen == PREMIUM else "DOWNGRADED -> cheap"
        print(f"#{i} {flag}")
        print(f"    premium estimate: ${est.predicted_cost}  ({est.predicted_input_tokens} in-tokens)")
        print(f"    chosen: {chosen}   measured: ${measured}\n")

    actual = costgen.total()
    print("-" * 60)
    print(f"If everything ran on {PREMIUM} (estimated): ${premium_estimate_total}")
    print(f"Actual spend with routing:                  ${actual}")
    saved = premium_estimate_total - actual
    if premium_estimate_total > 0:
        print(f"Saved by routing:                           ${saved} "
              f"({saved / premium_estimate_total:.0%})\n")
    costgen.print_report()
    if args.export:
        costgen.export(args.export)
        print(f"\nWrote structured export -> {args.export}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
