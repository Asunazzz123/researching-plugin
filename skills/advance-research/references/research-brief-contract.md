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

Experiments, simulation, field work, archival research, expert consultation,
secondary-data analysis, theoretical analysis, and data acquisition are peer
routes. Do not rank local execution higher by default.

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

## Cross-domain capability-gap examples

Apply one capability model across disciplines:

- geospatial work may require target layers, CRS, resolution, ground truth,
  licensing, data lineage, and a specific geoprocessing environment;
- clinical or social research may require governed populations, consent,
  privacy controls, ethics review, and authorized data access;
- field, ecological, archaeological, or qualitative research may require site
  access, sampling design, local context, interviews, or archival permission;
- wet-lab, hardware, and physical science may require instruments, calibration,
  materials, safety procedures, and environmental controls;
- proprietary-data research may require subscription entitlements, secure
  compute, contractual limits, and domain-specific validation.

When any required capability is absent, propose acquisition, collaboration,
remote execution, or protocol routes. Do not replace it with an unrelated local
experiment simply because local execution is available.
