# Changelog

All notable changes to costgen are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-06-29

Initial release.

### Added
- **Cost engine** — deterministic, provider-agnostic pricing of a normalized
  token `Usage` (input / output / cache-write / cache-read) with `Decimal` math.
- **Capture adapters**
  - `costgen.install()` — one-line auto-instrumentation of the OpenAI and
    Anthropic SDKs (incl. their Azure / Bedrock / Vertex / Foundry client classes
    and `langchain-openai`'s raw-response path).
  - `costgen.langchain_callback()` — LangChain / LangGraph callback handler.
  - `costgen.track(group, **tags)` — scoped attribution (feature / node / user).
  - `costgen.record(...)` / `costgen.wrap(...)` — explicit capture.
- **Estimation** — `costgen.estimate()` (Anthropic `count_tokens`, OpenAI
  `tiktoken`), kept distinct from measured cost.
- **Pricing** — bundled Anthropic + OpenAI prices with `source` + `last_verified`
  provenance; `set_price()` / `load_prices()` overrides; **alias resolution** for
  dated and cloud-prefixed/`@`-versioned model ids.
- **Reporting** — console report, JSON/CSV export, and a `costgen` CLI
  (`report` / `export` / `diff`).
- **Examples** — support-triage retrofit, LangGraph agent, FastAPI service with a
  budget guard, and a pre-flight estimate router (all runnable offline).

[Unreleased]: https://github.com/yashdixit0885/costgen/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yashdixit0885/costgen/releases/tag/v0.1.0
