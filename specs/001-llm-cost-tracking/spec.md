# Feature Specification: LLM Cost Tracking & Estimation (costgen v1)

**Feature Branch**: `001-llm-cost-tracking`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "costgen — an open-source Python package (pip/uv installable, publishable to PyPI as costgen) that developers embed in AI applications to track and predict the dollar cost of their LLM usage. One cost engine behind multiple thin capture adapters (auto-instrumentation via costgen.install(), decorator/context manager, explicit wrapper). Both pre-flight estimate and actual measurement. Anthropic + OpenAI in v1. Console/CLI report + structured export. Goal: let teams proactively cost-optimize their AI apps instead of reacting to a provider invoice."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Measure the actual cost of an existing app with one line (Priority: P1)

A developer maintaining an existing AI application wants to know what their LLM usage actually costs, without refactoring every call site. They add a single activation line at application startup. From then on, every LLM call the app makes through the supported provider SDKs (including calls issued by frameworks that route through those SDKs) is observed, priced from the provider's reported token usage, and rolled into a running total they can read and break down.

**Why this priority**: This is the core value proposition and the largest addressable audience (teams with apps already in production). Actual-cost measurement from observed usage is the most trustworthy number the tool can produce, and the one-line retrofit is what makes adoption realistic. If only this story ships, the product is already useful.

**Independent Test**: Run a sample app that makes several LLM calls across the supported providers, activate tracking with the single startup call, and confirm a correct total cost plus a per-call/per-model breakdown is produced — with zero changes to the app's call sites.

**Acceptance Scenarios**:

1. **Given** an application that makes LLM calls through a supported provider SDK, **When** the developer adds the one-line activation at startup and runs the app, **Then** every such call is captured and the reported total equals the sum of each call's measured cost.
2. **Given** a captured call whose response includes token usage, **When** cost is computed, **Then** the cost reflects that provider/model's input and output token prices and the result is labelled as a *measured* cost.
3. **Given** an application using a framework (e.g. LangChain/LangGraph/LlamaIndex) that issues its calls through a supported provider SDK, **When** tracking is active, **Then** those calls are captured without any framework-specific configuration.
4. **Given** a call routed through a path the tool does not auto-capture (e.g. a non-SDK HTTP path), **When** the app runs, **Then** that call is silently not counted and the tool does not error — and the limitation is documented.

---

### User Story 2 - See where the money goes and export it (Priority: P1)

After cost is being captured, a developer wants to understand and share where spend concentrates. They view a human-readable summary in the terminal (or via a CLI command) showing total cost broken down by provider, by model, and by logical grouping (e.g. feature or request), and they export the same data as a structured file so it can feed a CI check or downstream tooling.

**Why this priority**: Measurement is only actionable if the team can *see* and *route* the result. The breakdown is what turns a number into a decision ("model X in feature Y is 70% of our spend"), and the export is what enables proactive guardrails (cost diffs in CI). Together with Story 1 this is the minimum complete loop.

**Independent Test**: From a run with captured calls, produce a console/CLI report and a structured export, and confirm both contain the same totals and breakdowns (by provider, model, and grouping) and that the export is machine-readable.

**Acceptance Scenarios**:

1. **Given** a run with captured calls across multiple models, **When** the developer requests the report, **Then** a human-readable summary shows the grand total and a breakdown by provider and by model.
2. **Given** calls tagged with a logical group (e.g. a feature or request identifier), **When** the report is produced, **Then** cost is also broken down by that grouping and the per-group totals sum to the grand total.
3. **Given** a completed run, **When** the developer requests a structured export, **Then** a machine-readable file (suitable for ingestion by other tools) is written containing the same totals and breakdowns as the report.
4. **Given** an exported cost summary from a previous run, **When** a new run's export is compared against it, **Then** a consumer can detect a cost increase or decrease (enabling a CI cost-diff check).

---

### User Story 3 - Estimate cost before sending (Priority: P2)

A developer wants to know the likely cost of a request *before* it is sent — to budget, to choose between models, or to guard expensive calls. They ask the tool to estimate the cost of a prepared prompt for a given model, and receive a predicted cost clearly labelled as an estimate (distinct from a measured actual).

**Why this priority**: Pre-flight estimation enables the proactive optimization the product is positioned around (model selection, pre-send guards, budgeting), but it depends on the same pricing/tokenization foundation as measurement and is less critical than capturing real spend. It is high-value but a follow-on to the core measurement loop.

**Independent Test**: Provide a known prompt and target model, request an estimate, and confirm a predicted cost is returned, labelled as an estimate, and that the predicted token basis is reported alongside it.

**Acceptance Scenarios**:

1. **Given** a prepared prompt and a target model, **When** the developer requests a pre-flight estimate, **Then** a predicted cost is returned and is clearly labelled as an *estimate*, not a measured cost.
2. **Given** the same prompt is later actually sent and measured, **When** estimate and actual are compared, **Then** both are available and distinguishable, and the tool does not present the estimate as if it were the measured cost.
3. **Given** an estimate is requested for output cost where output length is unknown, **When** the estimate is produced, **Then** the assumption used for output length is reported so the prediction is interpretable.

---

### User Story 4 - Targeted and explicit tracking for uncovered or scoped cases (Priority: P2)

A developer wants to track cost for a specific block of code, attribute it to a named group, or capture calls that auto-instrumentation does not reach. They wrap the relevant region with a decorator or context manager (assigning a group/tag), or pass calls explicitly through the tool, and that cost is attributed to the chosen group and included in totals.

**Why this priority**: This is the universal fallback that guarantees *any* call can be tracked regardless of provider path, and it is how teams attribute cost to meaningful groupings. It complements auto-instrumentation rather than replacing it, so it sits just below the zero-touch path in priority.

**Independent Test**: Wrap a region of code with the context manager under a named group, make calls inside it (including via a path auto-instrumentation would miss), and confirm those calls are attributed to that group and included in the total.

**Acceptance Scenarios**:

1. **Given** a block wrapped with the tool's context manager/decorator under a named group, **When** LLM calls execute inside it, **Then** their cost is attributed to that group.
2. **Given** a call passed explicitly through the tool, **When** it completes, **Then** its measured cost is recorded and included in totals even if auto-instrumentation is not active.
3. **Given** both auto-instrumentation and an explicit wrapper observe the same single call, **When** cost is tallied, **Then** that call is counted exactly once (no double counting).

---

### Edge Cases

- **Missing/partial usage data**: A provider response omits or partially reports token usage → the call is recorded with measured cost where possible and clearly flagged as incomplete; it MUST NOT be silently priced as zero without indication.
- **Unknown model or missing price**: A call uses a model with no pricing record → the call is recorded and surfaced as "unpriced/unknown model" rather than dropped or priced as zero, so it cannot hide spend.
- **Streaming responses**: Usage may only be available at stream completion → cost is attributed once the stream finishes; an interrupted stream is recorded as incomplete.
- **Failed/aborted calls**: A call errors or is cancelled before completion → no measured cost is fabricated; any partial usage is recorded as such.
- **Tool internal failure**: Pricing data fails to load, an adapter cannot read a response, etc. → per Principle III, the tool logs and continues; the host application is never blocked, slowed beyond budget, or crashed.
- **Concurrency**: Many concurrent/async calls run at once → totals and per-group attribution remain correct under concurrency (no lost or double-counted calls).
- **Activated twice**: The activation/instrumentation is applied more than once → calls are still counted exactly once.
- **Stale pricing**: Loaded pricing data is older than the documented freshness cadence → the tool still runs and surfaces the data's `last_verified` date so the user can judge trust.
- **User price override**: A user supplies a custom price for a model → the override is used and the resulting cost is attributable to the override source rather than the bundled default.

## Requirements *(mandatory)*

### Functional Requirements

**Capture & Adapters**

- **FR-001**: The system MUST provide a single activation action that, once invoked at application startup, captures LLM calls made through the supported provider SDKs with no changes to existing call sites.
- **FR-002**: The system MUST capture calls issued by higher-level frameworks when those frameworks route through the supported provider SDKs, without framework-specific configuration.
- **FR-003**: The system MUST provide a decorator/context-manager mechanism to track a scoped region of code and attribute its calls to a caller-specified group/tag.
- **FR-004**: The system MUST provide an explicit mechanism to track an individual call passed through the tool, usable independently of auto-instrumentation.
- **FR-005**: The system MUST count each observed call exactly once even when more than one capture mechanism is active or activation is applied more than once.
- **FR-006**: The system MUST document which call paths are auto-captured in v1 and which are not (e.g. non-SDK HTTP, third-party router/abstraction layers, non-supported provider SDKs), and MUST allow uncaptured paths to be tracked via the scoped or explicit mechanisms.

**Cost Measurement & Estimation**

- **FR-007**: The system MUST compute a *measured* cost for a captured call from the token usage reported for that call and the applicable per-model input/output prices.
- **FR-008**: The system MUST provide a *pre-flight estimate* of a prepared request's cost for a specified model before the request is sent.
- **FR-009**: The system MUST clearly distinguish measured costs from estimated costs in every output and MUST NOT present an estimate as a measured actual.
- **FR-010**: For an estimate, the system MUST report the assumptions it relied on (e.g. assumed output length) so the prediction is interpretable.
- **FR-011**: The system MUST handle missing, partial, or unparseable usage data by recording the call and flagging it as incomplete rather than silently pricing it as zero.
- **FR-012**: The system MUST record a call whose model has no known price as "unpriced/unknown model" so unattributed spend is visible, never dropped.

**Pricing Data & Provenance**

- **FR-013**: The system MUST ship with bundled default pricing for the supported providers/models, and every pricing record MUST carry provenance including a `last_verified` date.
- **FR-014**: The system MUST allow a user to override or supplement pricing (e.g. for negotiated rates or new models) without requiring a new release of the package, and MUST attribute the resulting cost to the override source.
- **FR-015**: The system MUST surface the `last_verified` date (or staleness) of the pricing data used, so users can judge how current the figures are.
- **FR-016**: The system MUST support adding a new provider's pricing/tokenization as pluggable data/adapter without changes to the core cost-calculation logic.

**Attribution & Reporting**

- **FR-017**: The system MUST maintain a running total cost and MUST expose it programmatically to the host application during and after a run.
- **FR-018**: The system MUST break cost down by provider, by model, and by user-defined grouping/tag, and each breakdown's parts MUST sum to the grand total.
- **FR-019**: The system MUST produce a human-readable report (console output and/or a CLI command) summarizing total cost and the breakdowns above.
- **FR-020**: The system MUST produce a structured, machine-readable export of the same totals and breakdowns suitable for ingestion by CI checks and other tooling.
- **FR-021**: The structured export MUST be comparable across runs such that a consumer can detect a cost increase or decrease between two runs.

**Safety & Non-Intrusiveness**

- **FR-022**: Instrumentation MUST NOT raise into, block, or crash the host application; any internal failure MUST degrade gracefully (log and continue).
- **FR-023**: Cost tracking MUST remain correct (no lost or double-counted calls, correct per-group attribution) under concurrent and asynchronous call patterns.
- **FR-024**: Identical inputs to the cost-calculation logic MUST always produce identical cost outputs (deterministic math).

**Packaging & Adoption**

- **FR-025**: The package MUST be installable from the public package index via both `pip` and `uv`, and MUST declare its supported runtime versions explicitly.
- **FR-026**: The system MUST function with no configuration beyond the single activation action for the default measurement path (sensible defaults out of the box).

### Key Entities *(include if feature involves data)*

- **Tracked Call**: A single observed LLM invocation. Attributes: provider, model, input token count, output token count, measured cost, estimated cost (if applicable), completeness flag (complete/partial/unpriced), associated group/tag, timestamp, capture source (auto/scoped/explicit).
- **Pricing Record**: The price basis for a provider/model. Attributes: provider, model identifier, input price, output price (and any other priced usage dimensions), `last_verified` date, source/provenance, and whether it is a bundled default or a user override.
- **Cost Group / Tag**: A user-defined logical bucket (e.g. feature, request, user) calls are attributed to. Attributes: name and its rolled-up cost.
- **Cost Report / Export**: A point-in-time summary of a run. Attributes: grand total, breakdowns (by provider, model, group), measured-vs-estimated split, count of incomplete/unpriced calls, and the pricing-data freshness used.
- **Estimate**: A pre-send cost prediction. Attributes: target model, predicted input/output token basis, assumptions used (e.g. assumed output length), predicted cost, and an explicit "estimate" label.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can add cost measurement to an existing application by changing a single line at startup and, on the next run, see a correct total cost without editing any existing call site.
- **SC-002**: For calls whose provider reports token usage, the measured total cost matches an independent hand-calculation from the same token counts and published prices to within rounding (0 discrepancy in counts; cost differs only by defined rounding).
- **SC-003**: Every reported cost figure is unambiguously identifiable as either measured or estimated; a reviewer can tell which is which 100% of the time.
- **SC-004**: A team can identify the single highest-cost model and the single highest-cost group from the report in under 1 minute, without consulting the source code.
- **SC-005**: Cost tracking adds no more than a documented, bounded runtime overhead per call and never causes the host application to fail or hang, including when pricing data is missing or an internal error occurs.
- **SC-006**: Across concurrent runs, the sum of per-call costs equals the reported grand total in 100% of runs (no lost or double-counted calls).
- **SC-007**: A user can apply a custom/override price for a model and see it reflected in the next run's totals without upgrading or reinstalling the package.
- **SC-008**: The structured export from two runs can be diffed to flag a cost regression, enabling an automated CI cost check.
- **SC-009**: Every pricing figure presented to the user is traceable to a source and exposes a `last_verified` date.
- **SC-010**: The package installs cleanly via both `pip` and `uv` on a supported runtime in a clean environment.

## Assumptions

- **Provider scope (v1)**: Only Anthropic (Claude) and OpenAI model families are supported in v1; the pricing/tokenization design anticipates additional providers but they are out of scope for this release.
- **Auto-capture scope (v1)**: Auto-instrumentation targets the official provider SDKs. Calls that bypass those SDKs — third-party router/abstraction layers (e.g. LiteLLM), cloud-gateway SDKs (e.g. Bedrock/Vertex), and raw HTTP requests — are NOT auto-captured in v1 and must be tracked via the scoped or explicit mechanisms. This boundary is documented for users.
- **Token usage availability**: Measured cost relies on the provider returning token usage for completed (including completed streamed) responses; where usage is absent, the call is flagged incomplete rather than guessed.
- **Estimate fidelity**: Pre-flight estimates are predictions and may differ from measured actuals (especially for output tokens, whose length is not known before generation); estimates are clearly labelled and report their assumptions.
- **Runtime**: The library targets a modern Python runtime (per the project constitution, Python 3.11+) and is embedded in the host application's process; it is a library/CLI, not a hosted service.
- **Pricing freshness**: Bundled prices carry a `last_verified` date and are refreshed on a documented cadence; between refreshes, users can override prices locally.
- **Out of scope for v1**: Proxy / base-URL-swap capture mode; framework-native callback adapters (planned first fast-follow); HTTP-transport-layer instrumentation; hosted dashboard/UI; budget alerting/threshold enforcement; and any provider beyond Anthropic and OpenAI.
- **Cost currency**: Costs are reported in US dollars, consistent with how the supported providers publish prices.
