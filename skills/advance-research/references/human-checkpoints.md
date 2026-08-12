# Human checkpoints

The agent performs retrieval, organization, synthesis, criticism, and option
generation. The human owns scope, research taste, route choice, consequential
plans, execution, and final scientific claims.

## Checkpoint packet

At every human gate, present:

1. **Decision needed** — one concrete decision, not a generic request for feedback.
2. **Why now** — what evidence is sufficient and what cannot progress without a choice.
3. **Options** — two to four options with tradeoffs and a recommendation.
4. **Consequences** — required resources, side effects, cost, access, ethics, and reversibility.
5. **Approval boundary** — what the response will and will not authorize.
6. **Exact reference** — `RT-*`, `PR-*`, `T-*`, or named Claim set being reviewed.

## Scope checkpoint

Ask the human to confirm the bounded question and exclusions. Approval does not
select a research route or authorize implementation.

## Direction checkpoint

Ask the human to select, combine, revise, or reject route IDs from the research
brief. Record the selected IDs in the approval note. Approval authorizes detailed
planning only for those routes.

## Plan checkpoint

Show the exact protocol, dependencies, comparison, validation, budget, and stop
conditions. Approval freezes the scientific plan but does not authorize execution.

## Execution checkpoint

After Plan Gate approval, show commands or action class, external writes, data
movement, services contacted, expected duration/cost, and artifact paths. Require
an explicit response referring to the reviewed plan or actions.

The following phrases alone are **not** execution authorization:

- research or investigate this;
- make a demo;
- propose or implement a framework;
- do the first stage;
- continue;
- use your best judgment.

Examples of sufficiently explicit authorization:

- “Execute protocol PR-002 for task T-014 using only the reviewed inputs and actions.”
- “Run only the read-only validation steps in PR-001 on the supplied material; do not publish outputs.”

If the plan changes materially, discard the previous execution authorization and
return to Plan Gate.

## Claim checkpoint

Present bounded claims, supporting and contradicting evidence, limitations, and
remaining unknowns. Human acceptance closes the current research cycle, not the
entire scientific problem.

## Task participation checkpoints

- **H0 autonomous:** no advance human response is needed when validation is
  deterministic, read-only, and repeatable.
- **H1 batch-review:** present a batch summary and an auditable sample queue;
  the reports remain candidates until the reducer accepts them.
- **H2 checkpoint:** show competing candidates and ask the human to select,
  combine, revise, or reject them.
- **H3 collaborative:** issue a Human Handoff and resume only after the human
  returns the requested observations or artifacts.
- **H4 human-authority:** identify the accountable human decision or action;
  an Agent may prepare material but may not substitute for that authority.

A Human Handoff must state the action, prerequisites, quality requirements,
expected artifacts, bias and deviation fields, and the exact resume condition. It should
not expose internal chain-of-thought or ask for generic feedback.
