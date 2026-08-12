# Prompt operators

Load only the operator needed by the current research state. Treat each operator
as a pure transformation from inspected inputs to candidate records or a
research-brief section. Operators never approve a gate, mutate canonical state,
or grant execution authority.

## Shared contract

Provide:

- the bounded question, scope, non-goals, constraints, and glossary;
- relevant `U-*`, `E-*`, `C-*`, `AR-*`, `RT-*`, `WP-*`, `PR-*`, and `O-*` IDs;
- only the artifacts needed for this task;
- the target uncertainty and current human checkpoint;
- the frozen revision, context hash, output schema, and write scope.

Require:

- JSON-compatible candidate fragments, never a replacement canonical state;
- ID-backed grounding and source locators for detailed propositions;
- `unknown` rather than invented citations, observations, metrics, or results;
- explicit separation of observations, evidence, inference, and claims;
- assumptions, limitations, contradictions, and recommended next actions;
- no preference for a route merely because it can run locally.

## Frame

Use in `framing` or after a material scope change.

1. Convert the rough idea into one bounded research question.
2. Record contribution, scope, non-goals, constraints, resources, and stop
   conditions.
3. List decision-relevant uncertainties.
4. Identify judgments that require human taste or authority.

Return a `project` fragment and `U-*` candidates. Do not approve Scope Gate.

## Map domain and capabilities

Use after framing or when a route exposes missing context.

1. Identify the epistemic goal: description, explanation, prediction,
   evaluation, interpretation, design, or mixed.
2. Identify relevant units, populations or cases, periods, constructs,
   measurement or interpretation processes, and conventions.
3. Inventory data, tools, permissions, equipment, expertise, access, ethics,
   external systems, time, and compute.
4. Separate available capabilities from capabilities that must be supplied.
5. Identify invalid substitutions and proxy risks.

Return a capability map and terminology needing evidence. Do not start action.

## Ground

Use in `grounding` or when another stage exposes an evidence gap.

1. Map inspected Evidence Packets to the question.
2. Separate established context, disagreement, and missing evidence.
3. Identify nearest prior work or source material needed for comparison.
4. Produce precise searches for `$researching-paper-searching` where scholarly
   literature is the relevant source type.

Return `G-*` candidates with question, required source depth, decision reason,
and status. Never convert uninspected search results into Evidence Packets.

## Build working propositions

Use when the question benefits from alternative hypotheses, explanations,
interpretations, models, designs, or provisional judgments.

1. Generate genuinely distinct alternatives, including a simpler or null
   account and a plausible artifact or confound where applicable.
2. State what observations would distinguish or weaken each alternative.
3. Link supporting and contradicting Evidence IDs.
4. Identify the smallest information-gaining next step.

Return `WP-*` candidates. Do not force every research mode into a laboratory
hypothesis template.

## Criticize

Use before a consequential protocol, interpretation choice, or Claim Gate.
When possible, give the critic raw state and artifacts without the proposer's
persuasive narrative.

1. Find the strongest alternative account.
2. Test whether proposed observations distinguish the alternatives.
3. Identify leakage, confounds, proxy errors, circularity, selection effects,
   interpretive overreach, and metric gaming.
4. State what positive, negative, null, missing, or ambiguous observations mean.
5. Identify claims that exceed evidence depth or protocol scope.

Return objections with severity, affected IDs, required fix, and whether the
objection blocks the next gate. Never overwrite contrary evidence.

## Develop research routes

Use after domain mapping and grounding, before route-specific planning.

1. Generate two to four methodologically distinct routes.
2. For each `RT-*`, fill `epistemic_goal`, open `method_family`,
   `required_capabilities`, `executor_mix`, `validation_strategy`, and
   `uncertainty_ids`.
3. State information value, feasibility, risks, irreversible choices, expected
   artifacts or observations, and what the route cannot establish.
4. Reject convenient routes that do not reduce a target uncertainty.
5. Recommend a route and prepare a Direction Gate packet.

Return `RT-*` candidates. Do not select a route for the human.

## Decompose a route into tasks

Use after a route is selected and its required gate is approved.

1. Decompose the route into `T-*` nodes with explicit dependencies.
2. Assign `task_kind` by research role and H0-H4 by the nature of the action.
3. Declare input snapshots, isolated write scopes, resource locks, output
   contracts, validation, merge strategy, and required gate.
4. Split H3/H4 work into an explicit Human Handoff plus only those lower-level
   preparation or verification tasks that are independently safe.
5. Choose Map-Reduce, Portfolio, Proposer-Critic, Independent Replication, or
   sequential execution based on epistemic dependence.

Return Task Node candidates. Do not dispatch or edit canonical state.

## Design a protocol

Use after Direction Gate for any route requiring a reproducible action plan.

1. Define purpose, inputs, case or sample selection, observations or decisions,
   comparisons where applicable, quality controls, validation, and bias log.
2. Define artifact paths, resource needs, budget, stop and resume conditions.
3. State which outcomes inform which working propositions and which remain
   ambiguous.
4. Separate preparation, pilot or rehearsal, substantive action, and review.

Return a `PR-*` candidate. Do not approve Plan or Execution Gate and do not run it.

## Synthesize research brief

Follow `research-brief-contract.md`. Separate inspected evidence, synthesis,
unknowns, route portfolio, capability gaps, and recommendation. End with one
explicit human decision request.

## Interpret observations

Use after a returned report, Human Handoff, failed action, or unexpected event.

1. Inspect the referenced artifacts before summaries.
2. Record direct observations as `O-*` candidates.
3. Compare them with predeclared expectations, protocol, and quality criteria.
4. Record missingness, deviations, implementation threats, and limitations.
5. Propose bounded Claim candidates without erasing negative evidence.

Return `observations`, `evidence_candidates`, `claim_candidates`,
`contradictions`, `unknowns`, and `limitations`. A failed process is evidence
about that process unless the protocol justifies a broader inference.

## Decide next

Use in `deciding`, after criticism, or when several valid paths remain.

Generate at least three candidate next actions. For each, state target
uncertainties, prerequisites, expected information and decision value, cost,
risk, reversibility, H0-H4 level, and required gate. Scores are transparent
heuristics, not measurements. Recommend the action most likely to change the
decision per unit cost and risk, then stop at the applicable human checkpoint.
