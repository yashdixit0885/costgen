"""Cost-aware model router using costgen's pre-flight estimation.

Before sending, it estimates what a request would cost on the premium model. If
that exceeds a per-request cap, it routes to a cheaper model instead. This is the
"proactive" half of costgen: decide *before* you spend, not after.

    estimate(premium)  ->  over cap?  ->  use cheap model
                       ->  under cap? ->  use premium model
"""

from __future__ import annotations

from decimal import Decimal

import costgen

PREMIUM = "gpt-4o"
CHEAP = "gpt-4o-mini"


def route_and_answer(client, prompt: str, *, per_request_cap_usd: Decimal):
    """Estimate on the premium model; downgrade to cheap if over the cap. Returns
    (chosen_model, premium_estimate, measured_cost)."""
    messages = [{"role": "user", "content": prompt}]
    estimate = costgen.estimate(
        provider="openai", model=PREMIUM, messages=messages, assumed_output_tokens=150
    )

    over_budget = estimate.predicted_cost is not None and estimate.predicted_cost > per_request_cap_usd
    chosen = CHEAP if over_budget else PREMIUM

    before = costgen.total()
    with costgen.track(chosen):
        client.chat.completions.create(model=chosen, messages=messages, max_tokens=200)
    measured = costgen.total() - before
    return chosen, estimate, measured
