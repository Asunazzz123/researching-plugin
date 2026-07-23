# Research gates

Treat gates as human decision boundaries, not quality scores. Read-only research
may proceed between gates; route selection, planning, execution, and final claim
acceptance remain human-controlled.

## Scope Gate

Require this gate before treating a framing as stable.

- Record the question, intended contribution, scope, non-goals, material
  constraints, and decision context.
- Identify whether the work is explanatory, descriptive, predictive,
  interpretive, design-oriented, evaluative, or mixed.
- Ask the human to confirm the framing.

A material scope change returns to framing and resets direction, plan,
execution, and claim approvals.

## Evidence Gate

Apply continuously without requiring a ceremonial approval.

- Resolve every evidence reference to an Evidence Packet.
- Do not use metadata as support or contradiction.
- Require a locator for full-text or artifact claims.
- Preserve disagreement, incompatible definitions, scale mismatches, access
  limits, and inconclusive evidence.
- Mark what is inferred and what remains unknown.

Route literature gaps to `$researching-paper-searching` with the source depth
required by the downstream decision.

## Direction Gate

This is the default stopping point for the foundational skill.

Before the gate, present two to four research routes. Each route must state:

- the uncertainty it reduces and the expected decision value;
- the method family and validation strategy;
- required data, tools, compute, field access, expertise, permissions, and time;
- feasibility in the current environment;
- major risks, assumptions, and irreversible choices;
- the artifact or knowledge the route would produce.

Ask the human to select, combine, reject, or revise routes. Record the chosen
route IDs in the approval note. Do not infer a selection from silence or from a
general request to continue researching.

## Plan Gate

Use only after the Direction Gate selects an empirical or otherwise
consequential route.

- Design the protocol without executing it.
- Declare inputs, variables or observations, baselines, controls, sampling,
  validation, primary outputs, budget, stop conditions, and artifact paths.
- Disclose unavailable capabilities and external dependencies.
- Ask the human to approve the exact plan.

Plan approval authorizes planning completion, not execution.

## Execution Gate

Require a separate explicit authorization after Plan Gate approval and before
`piloting` or `experimenting`.

- Show the exact action class: commands, data transfer, external writes, API
  calls, cost, duration, privacy or ethics implications, and expected artifacts.
- Require approval that refers to the reviewed plan or named action.
- Never infer authorization from “research,” “investigate,” “demo,” “first
  stage,” “design,” or “propose an implementation.”
- If the plan changes materially, invalidate execution approval and return to
  Plan Gate.

When required infrastructure is unavailable, record the capability gap and
return a deployment or acquisition plan. Do not run a convenient but
scientifically unrelated local substitute.

## Interpretation and Claim Gate

After any observation or authorized execution:

- separate direct observations from interpretation;
- compare outcomes with predeclared expectations;
- retain negative, failed, null, and unexpected results;
- bound claims to the inspected sources, population, place, period, data,
  conditions, and measurement process;
- ask the human to approve the final bounded claim set.

Reaching a time or iteration limit is a stop condition, not scientific completion.
