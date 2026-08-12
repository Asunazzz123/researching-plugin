---
name: advance-research
description: Use when a researcher needs to frame a question, synthesize evidence, compare research routes, maintain a durable human-supervised research project, classify tasks by required human participation, parallelize bounded research work through sub-agents, resume human handoffs, or decide what research step to take next. Default to a research brief and Direction Gate; never infer authorization for consequential execution or final claims. Route literature gaps to researching-paper-searching.
---

# Advance Research

Build an auditable evidence-decision cycle. Keep research routes domain-neutral,
make human participation a first-class execution mode, and treat durable state as
an audit and coordination aid rather than the research method itself.

## Start with the foundational cycle

1. Frame the question, contribution, scope, non-goals, and decision context.
2. Map epistemic goals, material requirements, and unavailable capabilities.
3. Identify decision-relevant uncertainties.
4. Route literature gaps to `$researching-paper-searching` with the proposition,
   exclusions, terminology, source depth, and intended use.
5. Convert inspected sources into Evidence Packets; metadata is not claim evidence.
6. Preserve conflicts, access limits, incompatible scales, and unknowns.
7. Generate two to four `RT-*` routes described by epistemic goal, open method
   family, capabilities, executor mix, validation strategy, uncertainty, and risk.
8. Produce the research brief and stop at the Direction Gate.

Read [the research brief contract](references/research-brief-contract.md) before
writing the brief and [the prompt operators](references/prompt-kinds.md) only as
needed for the current stage.

For a project with `papers/index.md`, reload paper memory on resume, after a
stage or question change, when a conflict appears, and before stating what literature establishes.
These are evidence events, not fixed turn counts. Read
the selected paper records first and return to the original PDF locator when a
detailed claim depends on layout, equations, figures, tables, or extraction quality.

## Choose the operating mode

Use deliberation mode for a one-off brief. Do not create durable state merely
because local tools are available.

Use durable mode for a multi-session project, requested checkpoints, human
handoffs, or parallel task coordination. Validate an existing workspace first;
schema v2 does not auto-migrate older workspaces. Read:

- [state contract](references/state-contract.md);
- [task and human-level contract](references/task-node-contract.md);
- [sub-agent report contract](references/subagent-report-contract.md);
- [parallelization policy](references/parallelization-policy.md);
- [human checkpoints](references/human-checkpoints.md).

Commit canonical state only through the main-agent writer. Never hand-edit
`research_state.json`, `evidence.jsonl`, or `decisions.jsonl`.

## Classify human participation per task

- `H0`: autonomous, deterministic or reproducibly checked work.
- `H1`: batch work whose candidates are reviewed by summary or sampling.
- `H2`: candidate generation that must stop for a human checkpoint.
- `H3`: collaborative work requiring recurring human or expert judgment.
- `H4`: human authority or execution involving ethics, law, physical action,
  institutional responsibility, or final scientific claims.

Classify the action, not the discipline. Upgrade the level when uncertainty,
risk, tacit knowledge, access, or consequences increase. Never lower a recorded
level without an explicit human override in state.

## Orchestrate bounded sub-agent work

Use sub-agents only when two or more independent tasks justify the coordination
overhead. Keep the main agent as the sole scheduler and writer.

1. Create Task Nodes as a DAG in a candidate state.
2. Prepare each task's frozen Context Packet:

   ```bash
   python <skill-directory>/scripts/manage_tasks.py context <workspace> <task-id> --prepare
   ```

3. Select the deterministic non-conflicting frontier:

   ```bash
   python <skill-directory>/scripts/manage_tasks.py frontier <workspace> --max-parallel 3
   ```

4. Mark only the selected batch running:

   ```bash
   python <skill-directory>/scripts/manage_tasks.py start <workspace> <task-id> [<task-id> ...]
   ```

5. When sub-agent tools are available, dispatch at most three selected tasks.
   Give each agent only its `context.json`, require the report schema, forbid
   nested sub-agents, and restrict writes to that task's write scope.
6. Without sub-agent tools, execute the same frontier sequentially without
   changing task or report semantics.
7. Validate and merge each completed H0/H1 report:

   ```bash
   python <skill-directory>/scripts/manage_tasks.py validate-report <workspace> <report.json>
   python <skill-directory>/scripts/manage_tasks.py merge-report <workspace> <report.json>
   ```

H2 reports remain candidates for a human checkpoint. H3/H4 tasks do not enter
the automatic frontier; render a Human Handoff and stop for the required input:

```bash
python <skill-directory>/scripts/manage_tasks.py handoff <workspace> <task-id>
```

## Preserve consistency

- Let sub-agents report observations, evidence candidates, claim candidates,
  contradictions, unknowns, limitations, artifacts, and next actions separately.
- Merge records, not persuasive prose. Assign canonical IDs only in the reducer.
- Accept an older global revision only when the task-local context hash is still
  current; otherwise retain the report and mark the task `needs_rework`.
- Deduplicate by source lineage, not agent count. Preserve contradictory evidence
  in the conflict registry; agreement among agents is not independent evidence.
- Treat agent-created claims as `candidate`. Only the human Claim Gate can close
  a bounded claim set.

## Keep execution explicit

Direction approval authorizes planning only. Plan approval freezes the reviewed
protocol but does not authorize execution. Execution approval must identify the
commands or action class, external writes, data movement, costs, risks, duration,
and expected artifacts. A material protocol change resets Plan and Execution
approval.

Requests such as “research,” “investigate,” “make a demo,” “do the first stage,”
or “continue” do not authorize consequential execution. Missing data, access,
instruments, environments, expertise, permissions, or human practice require a
capability or handoff route, not a scientifically unrelated local substitute.

Stop at the Direction Gate by default. A completed brief means the decision is
ready for the researcher; it does not mean the scientific project is complete.
