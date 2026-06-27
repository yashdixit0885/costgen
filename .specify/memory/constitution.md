<!--
SYNC IMPACT REPORT
==================
Version change: (template/unversioned) → 1.0.0
Bump rationale: Initial ratification of the project constitution (MAJOR baseline).

Modified principles:
  - [PRINCIPLE_1] → I. Measurement Accuracy & Provenance
  - [PRINCIPLE_2] → II. Provider-Agnostic Core
  - [PRINCIPLE_3] → III. Non-Intrusive Integration (NON-NEGOTIABLE)
  - [PRINCIPLE_4] → IV. Test-First (NON-NEGOTIABLE)
  - [PRINCIPLE_5] → V. Public API Stability & Semantic Versioning
  - (added)       → VI. Minimal Footprint & Packaging Hygiene

Added sections:
  - Additional Constraints (technology, data, coverage policy)
  - Development Workflow (CI gates, review, open-source contribution standards)
  - Governance

Removed sections: none

Templates requiring updates:
  - ✅ .specify/templates/plan-template.md — Constitution Check gate is dynamic; reads this file, no edit needed
  - ✅ .specify/templates/tasks-template.md — updated: tests are MANDATORY (Principle IV), not optional
  - ✅ .specify/templates/spec-template.md — no constitution-mandated section changes required

Follow-up TODOs: none
-->

# TokenCostGenerator Constitution

TokenCostGenerator is an open-source Python library (installable via `pip` and `uv`) that
teams embed in their applications to measure the total cost of LLM token usage and inform
architecture decisions that reduce that cost. This constitution defines the non-negotiable
engineering principles every specification, plan, and task MUST satisfy.

## Core Principles

### I. Measurement Accuracy & Provenance

Every price and token figure the library reports MUST trace to an authoritative source (an
official provider pricing reference or the provider's tokenizer) and MUST carry a
`last_verified` date. Output MUST clearly distinguish *measured* costs (derived from observed
token counts) from *estimated* costs (derived from heuristics or projections). Pricing data
MUST never be silently hardcoded without provenance metadata.

Rationale: a cost tool exists to guide spending decisions; stale, unattributable, or
ambiguous numbers actively mislead the very decisions the tool is meant to support.

### II. Provider-Agnostic Core

Pricing and tokenization MUST be implemented as pluggable data adapters. The calculation
engine MUST contain no provider-specific branching. Adding support for a new provider MUST be
achievable by adding data and/or an adapter — never by editing core calculation logic.

Rationale: a stable, provider-neutral engine keeps the math trustworthy and lets the
community contribute new providers without risking regressions in existing ones.

### III. Non-Intrusive Integration (NON-NEGOTIABLE)

Instrumentation MUST NEVER raise into, block, or measurably degrade the host application. Any
internal failure MUST degrade gracefully — log and continue, never crash or stall the caller.
Runtime CPU and memory overhead MUST stay within a documented budget, and that budget MUST be
verified by tests or benchmarks.

Rationale: this library ships inside other teams' production applications; no team will adopt
a cost tool that can take down or slow the system it measures.

### IV. Test-First (NON-NEGOTIABLE)

Tests MUST be written and reviewed before the implementation they cover, and MUST be observed
to fail first. All cost-calculation logic MUST have deterministic unit tests: the same input
MUST always produce the same output. Cost-math modules MUST maintain 100% test coverage.

Rationale: financial calculations cannot be safely debugged in production after the fact;
correctness has to be proven up front and protected against regression.

### V. Public API Stability & Semantic Versioning

The public API is a contract with every team that depends on it. Releases MUST follow
Semantic Versioning: breaking changes require a MAJOR bump accompanied by migration notes;
backward-compatible additions are MINOR; fixes are PATCH. Internal-only code MUST be clearly
marked as non-public (e.g. a leading underscore or an explicit private module).

Rationale: teams pin and build on this library; surprise breakage erodes the trust that
open-source adoption depends on.

### VI. Minimal Footprint & Packaging Hygiene

Runtime dependencies MUST be kept minimal, and every new runtime dependency MUST be justified
during review. The package MUST install cleanly via both `pip` and `uv` and MUST declare its
supported Python versions explicitly. Optional or heavy capabilities MUST live behind optional
extras rather than the base install.

Rationale: every transitive dependency is a liability imposed on every downstream application;
a lean footprint is a feature, not an afterthought.

## Additional Constraints

- **Supported runtime**: Python 3.11 and newer. Support for an older version is a deliberate,
  documented decision — not the default.
- **Dependency policy**: Each new runtime dependency MUST be justified in the pull request that
  introduces it (why it is needed, why a lighter alternative was rejected).
- **Coverage policy**: Cost-math and calculation modules MUST hold 100% test coverage. Other
  modules SHOULD be well tested but are not held to the 100% bar.
- **Pricing data freshness**: The project MUST define and document a cadence for refreshing
  provider pricing data, and each pricing record MUST expose its `last_verified` date.

## Development Workflow

- **CI gate**: Continuous integration MUST pass before any merge. The 100% coverage gate on
  cost-math modules is enforced in CI.
- **Code review**: Every change MUST be reviewed via pull request before merge.
- **Open-source contribution standards**: The repository MUST provide a pull-request template
  and a documented review path for new provider adapters, so external contributions can be
  evaluated consistently and safely.

## Governance

This constitution supersedes ad-hoc practice; where a plan or task conflicts with it, the
constitution wins or the conflict MUST be explicitly justified in the plan's Complexity
Tracking section. Amendments MUST be proposed via pull request, documented in the Sync Impact
Report at the top of this file, and approved through normal review.

The constitution itself follows Semantic Versioning: MAJOR for backward-incompatible
governance or principle removals/redefinitions, MINOR for newly added or materially expanded
principles/sections, PATCH for clarifications and wording fixes. All reviews MUST verify that
proposed work complies with the principles above.

**Version**: 1.0.0 | **Ratified**: 2026-06-27 | **Last Amended**: 2026-06-27
