"""Serve the cost-aware FastAPI demo.

    python examples/fastapi_service/run.py          # offline (no keys) on :8000
    python examples/fastapi_service/run.py --live   # use real ANTHROPIC_API_KEY

Then, in another shell:

    curl -s localhost:8000/chat -H 'content-type: application/json' \
         -d '{"user":"alice","question":"What is a read replica?"}' | jq
    curl -s localhost:8000/costs | jq        # live spend, budget remaining, by user

The budget guard (COSTGEN_BUDGET_USD, default $0.05) makes /chat return 429 once
spend crosses the limit.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _enable_offline() -> None:
    """Patch the Anthropic SDK with canned responses BEFORE the app imports/installs."""
    from _offline_providers import patch_anthropic

    def profile(model, kwargs):
        # ~$0.0019 per call on haiku -> ~26 calls to reach the default $0.05 budget.
        return {"text": "Here's a concise, helpful answer to your question.",
                "input_tokens": 1500, "output_tokens": 200, "cache_read": 0}

    patch_anthropic(profile)


def main() -> int:
    ap = argparse.ArgumentParser(description="costgen FastAPI demo")
    ap.add_argument("--live", action="store_true", help="use real ANTHROPIC_API_KEY")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    if not args.live:
        _enable_offline()

    import uvicorn  # noqa: PLC0415

    # Import after offline patching so costgen.install() wraps the stubbed SDK.
    from app import app

    uvicorn.run(app, host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
