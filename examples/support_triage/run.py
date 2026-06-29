"""Run the support-triage app — with or without costgen — to see the difference.

    python examples/support_triage/run.py                  # the app as-is (no cost info)
    python examples/support_triage/run.py --with-costgen   # + ONE line: costgen.install()
    python examples/support_triage/run.py --with-costgen --export run.json
    python examples/support_triage/run.py --with-costgen --live   # use real API keys

The app code in `existing_app.py` is identical in every case — costgen attaches to
the SDK calls without any change there.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import existing_app  # noqa: E402  (after sys.path tweak so the demo is self-contained)


def parse_args():
    p = argparse.ArgumentParser(description="costgen support-triage demo")
    p.add_argument("--with-costgen", action="store_true",
                   help="add the one-line costgen.install() and print a cost report")
    p.add_argument("--live", action="store_true",
                   help="use real OpenAI/Anthropic API keys instead of the offline mock")
    p.add_argument("--export", metavar="PATH", help="write a structured cost export (JSON)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Offline by default so the demo runs with no keys / no network.
    if not args.live:
        import _offline
        _offline.enable()

    # ─────────────────────────────────────────────────────────────────────
    # The ONLY costgen-related change to make an existing app cost-aware:
    if args.with_costgen:
        import costgen
        costgen.install()
    # ─────────────────────────────────────────────────────────────────────

    results = existing_app.process_tickets(existing_app.TICKETS)
    print("Acme Cloud — support triage")
    print("-" * 48)
    for r in results:
        print(f"[{r['id']}] urgency={r['urgency']}")
        print(f"   {r['reply'][:80]}...")
    print(f"\nProcessed {len(results)} tickets.")

    if args.with_costgen:
        print()
        costgen.print_report()
        if args.export:
            costgen.export(args.export)
            print(f"\nWrote structured export -> {args.export}")
    else:
        print("\n(no cost visibility — run again with --with-costgen)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
