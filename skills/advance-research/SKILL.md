---
name: advance-research
description: Use when a researcher needs to frame a rough question, understand a field, resume project-local paper records, synthesize literature, build a concept and evidence map, compare research directions, expose resource or data gaps, or decide what research step to take next. Default to a cross-disciplinary, human-supervised research brief and decision checkpoint; do not assume a local experiment is possible or authorized. Experiment planning and execution are optional downstream branches requiring separate explicit human approvals. Route paper discovery gaps to researching-paper-searching.
---

# Advance Research

Build an auditable research understanding and hand consequential judgment back
to the researcher. Treat experiments as one possible research route, not as the
default destination.

## Default outcome

Produce a **research brief** and a **human decision checkpoint**. The brief must
answer:

1. What is the actual research question and epistemic goal?
2. What concepts, mechanisms, scales, populations, places, or time periods define it?
3. What does inspected evidence establish, contradict, or leave unknown?
4. Which competing explanations or interpretations remain plausible?
5. Which research routes are available, and what data, tools, access, expertise,
   ethics review, field work, compute, or external systems does each require?
6. Which decision must the human make next?

Read [references/research-brief-contract.md](references/research-brief-contract.md)
before writing the brief. Do not run an experiment merely because the current
machine can run one.

## Choose the operating mode

Use **deliberation mode by default**:

- perform read-only domain mapping, terminology expansion, source discovery,
  evidence synthesis, contradiction analysis, and feasibility assessment;
- represent experiments, simulation, field observation, archival work, expert
  consultation, data acquisition, and theoretical analysis as peer research routes;
- stop after presenting route options and the decision packet.

Use **durable mode** when the user requests artifacts, checkpoints, or a
multi-session project. Resume an existing `research_state.json`; otherwise
initialize a scoped workspace. Read
[references/state-contract.md](references/state-contract.md) before updates.

Use the **planning branch** only after the human selects a route. Use the
**execution branch** only after the human separately authorizes the exact plan
and its side effects. Read [references/human-checkpoints.md](references/human-checkpoints.md)
before treating any user message as approval.

## Run the foundational research cycle

1. Frame the question, intended contribution, scope, non-goals, and decision context.
2. Map the domain's epistemic mode and material requirements. Do not assume all
   fields use controlled local experiments.
3. Identify the largest decision-relevant uncertainties.
4. Load only the needed operator from
   [references/prompt-kinds.md](references/prompt-kinds.md).
5. Route literature gaps to `$researching-paper-searching`; include the exact
   proposition, exclusions, terminology, source depth, and intended use.
6. Convert inspected sources into Evidence Packets. Metadata is not claim evidence.
7. Build a concept/evidence map and preserve disagreement, missing data, access
   limits, incompatible scales, and method assumptions.
8. Generate two to four meaningfully different research routes. For each route,
   state information gain, decision relevance, required resources, feasibility,
   risks, validation strategy, and what cannot be done in the current environment.
9. Recommend a route only as a reasoned proposal. Present a human checkpoint and stop.

The cheapest next step may be another source search, obtaining missing data or
measurements, resolving a domain convention, requesting access, interviewing an
expert, checking an archive, inspecting an existing dataset, running a
simulation, or designing an experiment. Never equate “cheap” with “locally executable.”

## Keep execution optional and explicit

Do not infer execution authorization from requests such as “research this,”
“investigate,” “make a demo,” “propose an implementation,” or “do the first
stage.” These authorize research construction, not an unreviewed experiment.

Interpret a first-stage or framework demo as a demonstration of the research
brief, evidence map, route portfolio, and human checkpoint. Do not silently turn
it into a toy or synthetic-data experiment. Synthetic data are a valid route
only when the selected question concerns pipeline correctness, method behavior,
or pedagogy; they cannot establish substantive feasibility, identification,
external validity, or domain conclusions.

For an empirical route:

1. require the human to select the route at the Direction Gate;
2. design a protocol without executing it;
3. require approval of the exact protocol at the Plan Gate;
4. disclose commands, external writes, data use, cost, duration, and expected artifacts;
5. require a second explicit authorization at the Execution Gate;
6. return to the human if the plan changes materially.

Across disciplines, unavailable target data, populations, sites, instruments,
archives, licensed systems, governed environments, or domain expertise require
a capability-acquisition and validation plan. Record the gap; do not substitute
an unrelated local or synthetic experiment.

## Preserve evidence and process integrity

- Separate observation, evidence, interpretation, hypothesis, route, plan, and claim.
- Require locators for detailed source claims and record access depth.
- Label assumptions, limitations, failure conditions, and transfer boundaries.
- Preserve failed searches, inaccessible sources, tool gaps, and negative findings.
- Do not turn absence of evidence into novelty or feasibility.
- Do not let a polished narrative conceal a missing human decision.

## Refresh project-local paper memory

When the active research folder contains `papers/index.md`, use it as a compact
router into durable paper records. Read
[the project-local paper memory contract](../../references/paper-memory.md)
before managing or refreshing those records. This mechanism is independent of
durable research state and does not require a new state-machine transition.

Reload paper memory on research events, not fixed turn counts:

- on resume, read the index and the `30-second recall` plus `Open questions` of
  records relevant to the active question;
- after a material question, scope, comparison, population, data, or evaluation
  change, reselect relevant records from the index;
- on a stage change, reload results and conflicts for evidence synthesis,
  methods and limitations for route or protocol design, and proposition rows
  plus locators for writing or claim review;
- before stating what literature establishes, reload the relevant record and
  return to the located PDF page when the record is incomplete or disputed;
- after adding a paper or finding a conflict, reload related older records and
  update their cross-paper relationship.

Use progressive depth: `papers/index.md`, then the short recall, then relevant
record sections, then located PDF pages. Do not load the entire paper collection
on every research turn, and do not treat rereading as a decision-log event.

## Maintain durable state only when needed

Validate an existing workspace before reasoning:

```bash
python scripts/validate_state.py <workspace>
```

Commit candidate state only through `scripts/update_state.py`; never edit
canonical state or append-only logs by hand. The state harness is an audit aid,
not the research method itself. A one-off brief does not need a state machine
unless the user requests persistent tracking.

Stop at the Direction Gate by default. Completion of a research brief means the
decision is ready for the human; it does not mean the scientific project is complete.
