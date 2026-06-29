# Demo: cost-aware support triage (one-line retrofit)

A small but realistic "existing" AI app — a customer-support triage assistant —
and a demonstration that **one line** makes it cost-aware, with **zero changes to
the app code**.

The app ([`existing_app.py`](existing_app.py)) runs a 3-stage pipeline per ticket:

| Stage | Model | Why |
|------|-------|-----|
| classify urgency | OpenAI `gpt-4o-mini` | cheap, high volume |
| summarize issue | Anthropic `claude-haiku-4-5` | cheap, shared system prompt is cached |
| draft reply | Anthropic `claude-opus-4-8` | high quality — and the cost driver |

It has **no idea costgen exists** — it just calls the OpenAI and Anthropic SDKs
the normal way.

## Run it (no API keys needed)

The demo runs offline by default with realistic token usage, so you can try it
immediately:

```bash
pip install "costgen[all]"

# Before: the app as it is today — no cost visibility
python examples/support_triage/run.py

# After: the SAME app + one line  ->  costgen.install()
python examples/support_triage/run.py --with-costgen
```

## The one-line difference

That's the entire change to make an existing app cost-aware (from
[`run.py`](run.py)):

```python
import costgen
costgen.install()          # <-- the one line; existing_app.py is untouched

results = existing_app.process_tickets(existing_app.TICKETS)

costgen.print_report()     # see where the money goes
```

## What you see

```
costgen — LLM cost report
========================================
Grand total (measured): $0.125189 USD

By provider:
  anthropic          $0.125000
  openai             $0.000189

By model:
  claude-opus-4-8          $0.114750     <-- 92% of spend
  claude-haiku-4-5         $0.010250
  gpt-4o-mini              $0.000189
```

**The insight, instantly:** the Opus draft stage is ~92% of cost. That's your
optimization target — e.g. draft with `claude-sonnet-4-6` (\$3/\$15 vs \$5/\$25)
for routine tickets and reserve Opus for high-urgency ones, or cache more
aggressively. costgen turns "we'll find out when the invoice arrives" into a
number you can act on now.

## Attribute cost to features (optional)

`install()` already gives you per-provider and per-model breakdowns with zero app
changes. To also see cost **per feature**, wrap the stage you care about:

```python
with costgen.track("draft"):
    reply = draft_reply(ant, ticket, summary, urgency)
```

…and the report gains a "By group" section (`draft`, `classify`, …).

## Export for CI cost gates

```bash
python examples/support_triage/run.py --with-costgen --export run.json
costgen diff baseline.json run.json   # exits non-zero if cost regressed
```

## Use real providers

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
python examples/support_triage/run.py --with-costgen --live
```

In `--live` mode the costs are computed from the **actual** token usage each
provider reports — no mock.
