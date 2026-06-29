<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/001-llm-cost-tracking/plan.md`

## Active feature: costgen v1 — LLM Cost Tracking & Estimation
- **What**: open-source Python package (PyPI `costgen`) that AI apps embed to track + predict LLM dollar cost.
- **Stack**: Python 3.11+, `src/` layout, zero required runtime deps; `tiktoken`/provider SDKs behind optional extras (`costgen[openai]`, `costgen[anthropic]`). Tests: pytest + pytest-cov.
- **Architecture**: provider-agnostic cost engine (`costgen._engine`) behind thin capture adapters (`costgen._adapters`): `install()` auto-instrumentation of openai/anthropic SDKs, `track()` decorator/context-manager, `record()`/`wrap()` explicit.
- **Constitution gates**: measured-vs-estimated always distinct; every PricingRecord has `source`+`last_verified`; instrumentation never raises into the host app; cost math deterministic with 100% coverage; public API only in `costgen/__init__.py`.
- **Artifacts**: [plan](specs/001-llm-cost-tracking/plan.md) · [spec](specs/001-llm-cost-tracking/spec.md) · [research](specs/001-llm-cost-tracking/research.md) · [data-model](specs/001-llm-cost-tracking/data-model.md) · [contracts](specs/001-llm-cost-tracking/contracts/)
<!-- SPECKIT END -->
