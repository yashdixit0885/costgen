# Contributing to costgen

Thanks for helping make LLM cost tracking better. This project follows a small
set of non-negotiable engineering principles (see `.specify/memory/constitution.md`).

## Development setup

```bash
uv venv --python 3.11
uv pip install -e ".[all,dev]"
pytest                 # full suite
ruff check src tests   # lint
```

## Principles that gate every PR

- **Measurement accuracy & provenance.** Every price must carry a `source` and a
  `last_verified` date. Output must distinguish *measured* from *estimated* cost.
- **Provider-agnostic core.** `costgen/_engine/calculator.py` must never branch on
  a vendor name. A guard test enforces this.
- **Non-intrusive.** Instrumentation must never raise into, block, or crash the
  host app. Observation runs inside the `_safe` boundary.
- **Test-first.** Write failing tests before implementation. Cost-math modules
  (`_engine/calculator.py`) must hold **100% coverage** (enforced in CI).
- **Public API stability.** The public surface is `costgen/__init__.py`. Breaking
  changes require a MAJOR version bump and migration notes.
- **Minimal footprint.** No new required runtime dependency without justification;
  heavy/provider features go behind optional extras.

## Adding or updating pricing

1. Edit the relevant `src/costgen/_pricing/data/<provider>.json`.
2. Set the authoritative `source` URL and today's `last_verified` date.
3. Add/adjust a test asserting the new value.

## Adding a new provider adapter

The engine is pluggable by design — adding a provider should **not** touch the
calculator:

1. Add `src/costgen/_pricing/data/<provider>.json` (with provenance).
2. Add a usage parser `src/costgen/_adapters/<provider>.py` exposing
   `to_usage(raw) -> Usage | None`, and register it in `_adapters/normalize.py`.
3. (Optional) add an instrument `PatchSpec` for the provider's SDK.
4. (Optional) add an estimator under `_estimate/`.
5. Add unit + integration tests.

## Pull requests

- All CI checks (lint, tests, 100% cost-math coverage) must pass.
- Include tests for new behaviour; write them first and confirm they fail.
- Keep the public API change-surface small and documented.
