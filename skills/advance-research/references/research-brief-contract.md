# Research brief contract

Use this as the default deliverable before any route-specific plan. Adapt the
language to the discipline, but preserve the evidence and decision boundaries.

## Required sections

### 1. Research intent

- Restate the question and intended contribution.
- Identify who needs the answer and which decision it should inform.
- State scope, non-goals, spatial or temporal bounds, and important definitions.

### 2. Domain and capability map

- Identify the epistemic mode: descriptive, explanatory, predictive,
  interpretive, design-oriented, evaluative, or mixed.
- List relevant scales, units, populations, places, periods, constructs, and
  measurement processes.
- Separate resources available now from data, tools, access, expertise,
  permissions, instruments, field work, or compute that must be acquired.
- State which analyses cannot be validly performed in the current environment.

### 3. Evidence map

Organize inspected evidence by proposition, not paper order.

| Proposition | Evidence IDs | Support/conflict | Source depth | Boundary |
|---|---|---|---|---|

Keep metadata-only candidates, inaccessible sources, conflicting results, and
method incompatibilities visible.

### 4. Conceptual synthesis

- Explain how concepts, mechanisms, variables, actors, scales, or interpretations relate.
- Separate source-backed statements from synthesis and inference.
- Present competing explanations or interpretations where the domain supports them.
- State unresolved uncertainties in decision-relevant form.

### 5. Research route portfolio

Provide two to four meaningfully different routes.

Assign stable candidate IDs `RT-001`, `RT-002`, and so on, including in
one-session deliberation mode, so the human can approve an exact route boundary.

| Route ID | Method family | Uncertainty reduced | Requirements | Validation | Feasibility | Risk |
|---|---|---|---|---|---|---|

For every route, include:

- expected information and decision value;
- required data, access, tools, domain expertise, time, cost, and ethics review;
- what can be done now and what requires the researcher or an external environment;
- likely failure modes and what the route cannot establish;
- expected artifacts or observations.

Reject a route whose main advantage is that it can be demonstrated locally but
whose output would not reduce a decision-relevant uncertainty. Synthetic or toy
data may validate software plumbing or a method implementation only; label that
limited objective and never use it as a proxy for missing domain evidence.

Concrete method families are project-defined instances rather than core schema
categories. Do not rank a route higher merely because its tools are locally
available or its output is easy to produce.

### 6. Recommendation and human checkpoint

- Recommend one route or a staged combination, with evidence-backed reasons.
- State the strongest reason not to choose it.
- Identify the exact decision needed from the human.
- Stop before route-specific planning unless the human selects a route.

## Optional process ledger

When the user requests traceability, append an action table:

| Action | Purpose | Status | Evidence/artifact | Failure or limitation | Next adjustment |
|---|---|---|---|---|---|

Record searches, source inspection, access failures, tool gaps, assumptions,
route changes, and human decisions. Do not inflate the ledger with routine
internal reasoning that did not affect the research decision.

## Capability-gap patterns

Apply one orthogonal capability model across research settings:

- governed human or sensitive material may require consent, privacy controls,
  ethics review, institutional responsibility, and authorized access;
- direct observation may require site access, sampling or case-selection rules,
  local context, trained observers, and a deviation log;
- physical interaction may require equipment, calibration, materials, safety
  procedures, environmental controls, and accountable operators;
- controlled or proprietary sources may require entitlements, secure compute,
  contractual limits, source lineage, and domain-specific validation;
- abstract or computational work may still require specialist judgment,
  independently checked derivations, software, compute, or external replication.

When any required capability is absent, propose acquisition, collaboration,
remote execution, or a revised protocol. Do not replace it with an unrelated
local proxy merely because that proxy is executable.
