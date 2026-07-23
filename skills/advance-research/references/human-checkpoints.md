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
6. **Exact reference** — route ID, plan ID, or named claim set being reviewed.

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

- “Execute the approved EXP-002 plan using the listed local dataset and commands.”
- “Run only the read-only validation steps in PLAN-01 on the supplied data; do not publish outputs.”

If the plan changes materially, discard the previous execution authorization and
return to Plan Gate.

## Claim checkpoint

Present bounded claims, supporting and contradicting evidence, limitations, and
remaining unknowns. Human acceptance closes the current research cycle, not the
entire scientific problem.
