# Prompt operators

Load only the operator needed by the current research state. Treat each operator
as a pure transformation from inspected inputs to a research brief section or
structured candidate records. Operators do not grant execution authority.

## Shared contract

Provide the operator with:

- the current question, scope, non-goals, and constraints;
- relevant Evidence, Hypothesis, Experiment, and Result IDs;
- artifact contents needed for this decision;
- the specific uncertainty being reduced.
- the domain's epistemic mode and known material constraints;
- the current human checkpoint and any explicitly selected route IDs.

Require it to:

- return JSON-compatible state fragments, not a replacement canonical state;
- cite IDs for every grounded statement;
- return `unknown` instead of inventing evidence, citations, metrics, or results;
- separate observation, inference, hypothesis, and claim;
- state important assumptions and failure conditions;
- avoid selecting an action only because it is easy or likely to look positive.
- avoid preferring an action merely because it can run on the current machine.

## Frame

Use for `framing` or after a material scope change.

Task:

1. Convert the rough idea into one bounded research question.
2. Identify scope, non-goals, operational variables, constraints, resources, and
   stop conditions.
3. List decision-relevant uncertainties rather than generic open questions.
4. Identify what requires human taste or approval.

Return a `project` object, `U-*` uncertainty records, and stop conditions. Do not
mark Scope Gate approved.

## Map domain and feasibility

Use after framing, especially for cross-disciplinary work or unfamiliar domains.

Task:

1. Identify whether the intended knowledge is descriptive, explanatory,
   predictive, interpretive, design-oriented, evaluative, or mixed.
2. Identify relevant scales, populations, spatial or temporal units, constructs,
   measurement processes, and domain conventions.
3. Inventory required data, formats, instruments, software, licenses, expertise,
   ethics review, field access, remote services, and compute.
4. Separate capabilities available now from capabilities that must be acquired
   or supplied by the researcher.
5. Identify invalid substitutions. A convenient local proxy cannot replace the
   field's decision-relevant data, population, instrument, archive, licensed
   system, physical environment, spatial context, or validation process.

Return a `domain_map`, a capability matrix, terminology that needs evidence, and
material constraints. Do not start implementation or experimentation.

## Ground

Use for `grounding` or when another stage exposes an evidence gap.

Task:

1. Map existing Evidence Packets to the question.
2. Separate established context, conflicting evidence, and missing evidence.
3. Identify the nearest prior work needed for novelty comparison.
4. Produce precise searches for `$researching-paper-searching`.

Return `G-*` records shaped as:

```json
{
  "id": "G-001",
  "question": "Exact proposition that needs evidence",
  "required_source_depth": "full_text",
  "reason": "Which decision or claim depends on it",
  "status": "open"
}
```

Do not convert uninspected paper candidates into Evidence Packets.

## Build explanations or working propositions

Use after grounding when the question benefits from competing explanations.
Descriptive, interpretive, historical, or design research may instead use
competing interpretations, models, or propositions; do not force every field
into a laboratory hypothesis template.

Task:

1. Generate three to five genuinely competing mechanistic explanations.
2. Include a simpler/null explanation and a plausible artifact or confound.
3. Give each hypothesis differentiating predictions and falsifiers.
4. Link supporting and contradicting Evidence IDs.
5. Identify the cheapest information-gaining step that distinguishes alternatives.
   It may be literature, data access, expert review, archival work, field
   observation, simulation, or experiment.

Return `H-*` records following `state-contract.md`. Keep novelty as a bounded
delta from named nearest work; do not equate missing search results with novelty.

## Criticize

Use before experiment approval and before Claim Gate. When possible, run it with
only the raw state and artifacts, without the proposer’s persuasive narrative.

Task:

1. Find the strongest alternative explanation.
2. Test whether predictions actually distinguish hypotheses.
3. Identify leakage, confounds, proxy measures, circularity, and metric gaming.
4. Ask what a positive, negative, and null result would each mean.
5. Identify claims that exceed source depth or experiment design.

Return objections with severity, affected IDs, required fix, and whether the
objection blocks the next gate. Criticism never edits evidence in place.

## Develop research routes

Use after domain mapping and grounding, before any implementation plan.

Task:

1. Generate two to four methodologically distinct routes rather than variations
   of one favored method.
2. Include a non-experimental route when it is scientifically plausible.
3. For each route, state the uncertainty reduced, expected information gain,
   decision relevance, required resources, feasibility, risks, ethics/access
   constraints, validation strategy, and expected artifact.
4. State what cannot be established by the route.
5. Reject locally convenient toy or synthetic routes that do not reduce a
   decision-relevant uncertainty.
6. Recommend a route with reasons, then prepare a Direction Gate checkpoint.

Return `A-*` route records plus a human decision packet. Do not select a route on
the human's behalf and do not design an experiment yet.

## Synthesize research brief

Use when evidence and route options are sufficient for a human decision.

Follow `research-brief-contract.md`. Separate established evidence, synthesis,
unknowns, route options, and recommendation. Include source-access limitations
and capability gaps. End with one explicit decision request.

## Design optional empirical plan

Use only after the human selects an empirical route at Direction Gate and at
least one testable hypothesis or proposition exists.

Task:

1. Choose the smallest experiment with high decision-relevant information gain.
2. Predeclare variables, baselines, controls, primary metric, budget, and stop
   conditions.
3. State which outcome favors which hypothesis and which outcomes are ambiguous.
4. Define artifact paths before execution.
5. Separate a pilot from a full experiment.

Return an `EXP-*` record following `state-contract.md`. Do not mark Experiment
or Execution Gate approved. Do not execute the plan.

## Interpret

Use after any pilot, experiment, failed run, or unexpected observation.

Task:

1. Read raw artifacts before summaries.
2. Record direct observations and metrics in an `R-*` record.
3. Compare outcomes with predeclared predictions and stop conditions.
4. Identify unexpected findings, implementation threats, and limitations.
5. Propose bounded Claim updates without erasing negative evidence.

Return four labeled groups: `observations`, `inferences`, `claim_updates`, and
`unknowns`. A failed pipeline is a result about the pipeline, not evidence for or
against the scientific hypothesis unless the design says otherwise.

## Decide next

Use for `deciding`, after criticism, or when several valid paths remain.

Generate at least three `A-*` candidate actions. For each record:

```json
{
  "id": "A-001",
  "action": "Concrete next action",
  "resolves_uncertainty_ids": ["U-001"],
  "expected_information_gain": 0.8,
  "decision_relevance": 0.9,
  "cost": 0.2,
  "risk": 0.1,
  "prerequisites": [],
  "status": "candidate"
}
```

Use the scores as transparent heuristics, not measurements. Present the routes
to the human and recommend the action most likely to change the research
decision per unit cost and risk. Do not mark it selected until the Direction
Gate records the human choice. Return to grounding or route construction when
the result weakens current assumptions. Recommend `claim_review` only when
remaining uncertainties do not materially change the bounded claim.
