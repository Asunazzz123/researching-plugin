from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).parents[1]
SCRIPTS = PLUGIN_ROOT / "skills" / "advance-research" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from research_state import (  # noqa: E402
    CANONICAL_WRITER,
    SCHEMA_VERSION,
    create_workspace,
    initial_state,
    load_state,
    update_workspace,
    validate_or_raise,
    validate_workspace,
)
from task_orchestration import (  # noqa: E402
    merge_report,
    prepare_task_context,
    ready_frontier,
    render_handoff,
    start_tasks,
    task_context_hash,
    validate_report,
)


def task_record(
    task_id: str,
    *,
    human_level: str = "H0",
    executor: str = "subagent",
    depends_on: list[str] | None = None,
    resource_locks: list[str] | None = None,
    priority: int = 50,
    merge_strategy: str = "append_candidates",
    may_propose_evidence: bool = True,
    may_propose_claims: bool = False,
) -> dict:
    handoff = None
    if human_level in {"H3", "H4"}:
        handoff = {
            "action": "Perform the authorized domain action and record deviations.",
            "prerequisites": ["Required access is available"],
            "quality_requirements": ["Record provenance and missing observations"],
            "expected_artifacts": ["A documented observation artifact"],
            "bias_fields": ["Potential selection or observer bias"],
            "deviation_fields": ["Departure from protocol"],
            "resume_condition": "Return the artifact and observation record.",
        }
    return {
        "id": task_id,
        "parent_task_id": None,
        "title": f"Task {task_id}",
        "task_kind": "extract",
        "epistemic_role": "evidence_acquisition",
        "question": "What inspected evidence bears on the bounded uncertainty?",
        "uncertainty_ids": [],
        "human_level": human_level,
        "human_level_override": None,
        "executor": executor,
        "status": "draft",
        "depends_on": depends_on or [],
        "priority": priority,
        "input_snapshot": {
            "research_revision": None,
            "context_hash": None,
            "route_ids": [],
            "protocol_ids": [],
            "evidence_ids": [],
            "claim_ids": [],
            "artifact_ids": [],
        },
        "execution": {
            "mode": "read_only",
            "read_scope": [],
            "write_scope": f"orchestration/tasks/{task_id}",
            "resource_locks": resource_locks or [],
            "side_effects": ["none"],
            "parallel_group": "source-review",
        },
        "output_contract": {
            "artifact_types": ["agent_report"],
            "may_propose_evidence": may_propose_evidence,
            "may_propose_claims": may_propose_claims,
        },
        "validation": {
            "mode": "schema_and_source",
            "requires_human": human_level not in {"H0", "H1"},
            "acceptance_criteria": ["Every detailed proposition has a locator"],
        },
        "merge": {
            "strategy": merge_strategy,
            "conflict_policy": "preserve_and_escalate",
            "required_gate": None,
        },
        "human_handoff": handoff,
    }


def completed_report(task_id: str, context_hash: str, revision: int) -> dict:
    evidence_id = f"{task_id}:E-1"
    return {
        "report_id": f"REP-{task_id}-001",
        "task_id": task_id,
        "based_on_revision": revision,
        "context_hash": context_hash,
        "status": "completed",
        "actions": [{"action": "inspect source", "outcome": "located proposition"}],
        "observations": [],
        "evidence_candidates": [
            {
                "id": evidence_id,
                "proposition": "The inspected source supports a bounded proposition.",
                "stance": "supports",
                "source_kind": "literature",
                "source_id": "doi:10.example/source",
                "source_lineage": "doi:10.example/source",
                "source_depth": "full_text",
                "locator": {"page": 7},
                "limitations": ["Applies only to the inspected setting"],
                "confidence": 0.8,
            }
        ],
        "claim_candidates": [],
        "contradictions": [],
        "unknowns": ["Transfer to other settings is unknown"],
        "limitations": ["One inspected source"],
        "artifacts": [],
        "recommended_next_actions": [],
    }


class ResearchStateV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name) / "research"
        self.state = initial_state(
            "How should a bounded research uncertainty be reduced?",
            scope=["One explicit uncertainty"],
        )
        create_workspace(self.workspace, self.state)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def commit(self, candidate: dict, action: str = "test update") -> dict:
        update_workspace(
            self.workspace,
            candidate,
            action=action,
            rationale="exercise a schema-v2 invariant",
            actor=CANONICAL_WRITER,
        )
        return load_state(self.workspace / "research_state.json")

    def add_task(self, task: dict) -> dict:
        state = load_state(self.workspace / "research_state.json")
        candidate = deepcopy(state)
        candidate["tasks"].append(task)
        return self.commit(candidate, f"add {task['id']}")

    def run_task(self, task_id: str) -> tuple[dict, dict]:
        prepared = prepare_task_context(self.workspace, task_id)
        state = load_state(self.workspace / "research_state.json")
        candidate = deepcopy(state)
        next(item for item in candidate["tasks"] if item["id"] == task_id)["status"] = "assigned"
        state = self.commit(candidate, f"assign {task_id}")
        candidate = deepcopy(state)
        next(item for item in candidate["tasks"] if item["id"] == task_id)["status"] = "running"
        state = self.commit(candidate, f"run {task_id}")
        return state, prepared["packet"]

    def test_initializes_domain_neutral_workspace(self) -> None:
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual(state["schema_version"], "2.0")
        self.assertEqual(state["current_stage"], "framing")
        for collection in (
            "routes", "working_propositions", "protocols", "observations",
            "tasks", "artifacts", "conflicts",
        ):
            self.assertEqual(state[collection], [])
        for path in (
            "artifacts", "orchestration/tasks", "orchestration/reports", ".checkpoints"
        ):
            self.assertTrue((self.workspace / path).is_dir())
        summary = (self.workspace / "research_summary.md").read_text(encoding="utf-8")
        for queue in ("ready", "running", "waiting-human", "conflict", "stale-report"):
            self.assertIn(f"| {queue} |", summary)
        self.assertEqual(validate_workspace(self.workspace), [])

    def test_rejects_unknown_schema_without_automatic_migration(self) -> None:
        path = self.workspace / "research_state.json"
        payload = json.loads(path.read_text())
        payload["schema_version"] = "1.0"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unsupported schema_version"):
            load_state(path)

    def test_only_main_agent_can_write_canonical_state(self) -> None:
        with self.assertRaisesRegex(ValueError, "only be written"):
            update_workspace(
                self.workspace,
                self.state,
                action="subagent write",
                rationale="must fail",
                actor="subagent",
            )

    def test_route_selection_requires_human_direction(self) -> None:
        candidate = deepcopy(load_state(self.workspace / "research_state.json"))
        candidate["current_stage"] = "planning"
        with self.assertRaisesRegex(ValueError, "Direction Gate"):
            validate_or_raise(candidate, previous=load_state(self.workspace / "research_state.json"))

    def test_scope_plan_execution_and_claim_gates_are_enforced(self) -> None:
        state = load_state(self.workspace / "research_state.json")

        scope_candidate = deepcopy(state)
        scope_candidate["current_stage"] = "grounding"
        with self.assertRaisesRegex(ValueError, "Scope Gate"):
            validate_or_raise(scope_candidate)

        plan_candidate = deepcopy(state)
        plan_task = task_record("T-001")
        plan_task["merge"]["required_gate"] = "plan"
        plan_task["input_snapshot"]["research_revision"] = state["revision"]
        plan_task["input_snapshot"]["context_hash"] = "0" * 64
        plan_task["status"] = "ready"
        plan_candidate["tasks"] = [plan_task]
        with self.assertRaisesRegex(ValueError, "required plan gate"):
            validate_or_raise(plan_candidate)

        execution_candidate = deepcopy(state)
        execution_task = task_record("T-001")
        execution_task["execution"]["mode"] = "execute_external"
        execution_task["input_snapshot"]["research_revision"] = state["revision"]
        execution_task["input_snapshot"]["context_hash"] = "0" * 64
        execution_task["status"] = "ready"
        execution_candidate["tasks"] = [execution_task]
        with self.assertRaisesRegex(ValueError, "Execution Gate"):
            validate_or_raise(execution_candidate)

        claim_candidate = deepcopy(state)
        claim_candidate["current_stage"] = "complete"
        with self.assertRaisesRegex(ValueError, "Claim Gate"):
            validate_or_raise(claim_candidate)

    def test_task_graph_rejects_cycle(self) -> None:
        candidate = deepcopy(load_state(self.workspace / "research_state.json"))
        first, second = task_record("T-001"), task_record("T-002")
        first["depends_on"] = ["T-002"]
        second["depends_on"] = ["T-001"]
        candidate["tasks"] = [first, second]
        with self.assertRaisesRegex(ValueError, "task dependency cycle"):
            validate_or_raise(candidate)

    def test_task_graph_rejects_missing_dependency(self) -> None:
        candidate = deepcopy(load_state(self.workspace / "research_state.json"))
        candidate["tasks"] = [task_record("T-001", depends_on=["T-999"])]
        with self.assertRaisesRegex(ValueError, "depends_on references unknown ids"):
            validate_or_raise(candidate)

    def test_task_read_scope_must_cover_referenced_artifacts(self) -> None:
        candidate = deepcopy(load_state(self.workspace / "research_state.json"))
        candidate["artifacts"].append({
            "id": "AR-001",
            "path": "artifacts/input.txt",
            "sha256": "0" * 64,
            "media_type": "text/plain",
            "description": "Declared input",
            "provenance": "Supplied fixture",
            "status": "available",
        })
        task = task_record("T-001")
        task["input_snapshot"]["artifact_ids"] = ["AR-001"]
        candidate["tasks"] = [task]
        with self.assertRaisesRegex(ValueError, "read_scope omits input artifacts"):
            validate_or_raise(candidate)
        task["execution"]["read_scope"] = ["artifacts/input.txt"]
        validate_or_raise(candidate)

    def test_lowering_human_level_requires_override(self) -> None:
        self.add_task(task_record("T-001", human_level="H3", executor="shared"))
        state = load_state(self.workspace / "research_state.json")
        candidate = deepcopy(state)
        task = candidate["tasks"][0]
        task["human_level"] = "H1"
        task["human_handoff"] = None
        with self.assertRaisesRegex(ValueError, "lowering human_level"):
            validate_or_raise(candidate, previous=state)

    def test_frontier_is_deterministic_and_respects_resource_locks(self) -> None:
        self.add_task(task_record("T-001", priority=80, resource_locks=["licensed-index"]))
        self.add_task(task_record("T-002", priority=70, resource_locks=["licensed-index"]))
        self.add_task(task_record("T-003", priority=60))
        for task_id in ("T-001", "T-002", "T-003"):
            prepare_task_context(self.workspace, task_id)
        state = load_state(self.workspace / "research_state.json")
        result = ready_frontier(state, max_parallel=3)
        self.assertEqual([item["task_id"] for item in result["selected"]], ["T-001", "T-003"])
        self.assertIn("resource lock conflict", next(item["reason"] for item in result["deferred"] if item["task_id"] == "T-002"))
        self.assertEqual(result, ready_frontier(state, max_parallel=3))

    def test_frontier_never_exceeds_three_tasks(self) -> None:
        for index in range(1, 5):
            task_id = f"T-{index:03d}"
            self.add_task(task_record(task_id, priority=100 - index))
            prepare_task_context(self.workspace, task_id)
        result = ready_frontier(load_state(self.workspace / "research_state.json"), max_parallel=99)
        self.assertEqual(result["max_parallel"], 3)
        self.assertEqual(len(result["selected"]), 3)
        self.assertIn("parallel limit", next(item["reason"] for item in result["deferred"] if item["task_id"] == "T-004"))

    def test_h2_can_only_dispatch_candidate_work(self) -> None:
        self.add_task(task_record("T-001", human_level="H2", merge_strategy="human_checkpoint"))
        prepare_task_context(self.workspace, "T-001")
        result = ready_frontier(load_state(self.workspace / "research_state.json"))
        self.assertEqual(result["selected"][0]["dispatch_mode"], "candidate_only")

    def test_start_marks_only_a_validated_frontier_batch_running(self) -> None:
        self.add_task(task_record("T-001", priority=80))
        self.add_task(task_record("T-002", priority=70))
        for task_id in ("T-001", "T-002"):
            prepare_task_context(self.workspace, task_id)
        result = start_tasks(self.workspace, ["T-001", "T-002"])
        self.assertEqual(result["task_ids"], ["T-001", "T-002"])
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual([task["status"] for task in state["tasks"]], ["running", "running"])

    def test_h4_generates_handoff_instead_of_frontier_work(self) -> None:
        self.add_task(task_record("T-001", human_level="H4", executor="human"))
        prepare_task_context(self.workspace, "T-001")
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual(state["tasks"][0]["status"], "waiting_human")
        self.assertIn("Human Handoff", render_handoff(state, "T-001"))
        self.assertEqual(ready_frontier(state)["selected"], [])

    def test_human_task_can_pause_and_resume_as_reported(self) -> None:
        self.add_task(task_record("T-001", human_level="H3", executor="shared"))
        prepare_task_context(self.workspace, "T-001")
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual(state["tasks"][0]["status"], "waiting_human")
        candidate = deepcopy(state)
        candidate["tasks"][0]["status"] = "reported"
        resumed = self.commit(candidate, "record returned human handoff material")
        self.assertEqual(resumed["tasks"][0]["status"], "reported")

    def test_cross_practice_tasks_share_one_participation_model(self) -> None:
        fixtures = (
            task_record("T-001", human_level="H0", executor="subagent"),
            task_record("T-002", human_level="H1", executor="subagent"),
            task_record("T-003", human_level="H3", executor="shared"),
            task_record("T-004", human_level="H4", executor="human"),
        )
        fixtures[0]["title"] = "Check an independently reproducible derivation"
        fixtures[1]["title"] = "Normalize supplied secondary records"
        fixtures[2]["title"] = "Record context-dependent observations"
        fixtures[3]["title"] = "Confirm the accountable final research claim"
        for task in fixtures:
            self.add_task(task)
            prepare_task_context(self.workspace, task["id"])
        state = load_state(self.workspace / "research_state.json")
        frontier = ready_frontier(state)
        self.assertEqual([item["task_id"] for item in frontier["selected"]], ["T-001", "T-002"])
        self.assertEqual(
            [task["status"] for task in state["tasks"][2:]],
            ["waiting_human", "waiting_human"],
        )

    def test_context_hash_ignores_unrelated_revision_changes(self) -> None:
        self.add_task(task_record("T-001"))
        prepared = prepare_task_context(self.workspace, "T-001")
        old_hash = prepared["packet"]["context_hash"]
        state = load_state(self.workspace / "research_state.json")
        candidate = deepcopy(state)
        candidate["stop_conditions"].append("Stop after the review window")
        state = self.commit(candidate, "add unrelated stop condition")
        self.assertEqual(task_context_hash(state, state["tasks"][0]), old_hash)

    def test_context_packet_contains_an_executable_report_contract(self) -> None:
        self.add_task(task_record("T-001"))
        packet = prepare_task_context(self.workspace, "T-001")["packet"]
        contract = packet["report_contract"]
        self.assertEqual(contract["report_id_pattern"], "REP-T-001-<identifier>")
        self.assertEqual(contract["based_on_revision"], packet["research_revision"])
        self.assertIn("source_lineage", contract["evidence_candidate"]["types"])
        self.assertIn("Do not copy referenced input artifacts", contract["artifact"]["boundary"])

    def test_report_requires_locator_and_respects_write_scope(self) -> None:
        self.add_task(task_record("T-001"))
        state, packet = self.run_task("T-001")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        report["evidence_candidates"][0]["locator"] = {}
        errors = validate_report(self.workspace, report)
        self.assertTrue(any("locator" in error for error in errors))

    def test_reducer_maps_ids_and_merges_only_candidates(self) -> None:
        task = task_record("T-001", may_propose_claims=True)
        self.add_task(task)
        state, packet = self.run_task("T-001")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        report["claim_candidates"] = [
            {
                "id": "T-001:C-1",
                "statement": "A bounded candidate claim.",
                "evidence_ids": ["T-001:E-1"],
                "observation_ids": [],
                "caveats": ["Requires human Claim Gate"],
            }
        ]
        result = merge_report(self.workspace, report)
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual(result["status"], "merged")
        self.assertEqual(state["tasks"][0]["status"], "merged")
        self.assertEqual(state["evidence"][0]["id"], "E-001")
        self.assertEqual(state["claims"][0]["status"], "candidate")
        self.assertEqual(state["claims"][0]["evidence_ids"], ["E-001"])

    def test_failed_report_is_retained_as_unmerged_work(self) -> None:
        self.add_task(task_record("T-001"))
        state, packet = self.run_task("T-001")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        report["status"] = "failed"
        report["evidence_candidates"] = []
        report["unknowns"].append("The task failed before evidence extraction completed")
        result = merge_report(self.workspace, report)
        current = load_state(self.workspace / "research_state.json")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(Path(result["report_path"]).is_file())
        self.assertEqual(current["tasks"][0]["status"], "blocked")
        self.assertEqual(current["evidence"], [])

    def test_h2_through_h4_cannot_use_the_automatic_reducer(self) -> None:
        for index, (level, executor) in enumerate(
            (("H2", "subagent"), ("H3", "shared"), ("H4", "human")), start=1
        ):
            task_id = f"T-{index:03d}"
            task = task_record(
                task_id,
                human_level=level,
                executor=executor,
                merge_strategy="human_checkpoint",
            )
            self.add_task(task)
            prepared = prepare_task_context(self.workspace, task_id)
            state = load_state(self.workspace / "research_state.json")
            candidate = deepcopy(state)
            next(item for item in candidate["tasks"] if item["id"] == task_id)["status"] = "running"
            self.commit(candidate, f"record returned work for {task_id}")
            report = completed_report(
                task_id,
                prepared["packet"]["context_hash"],
                prepared["packet"]["research_revision"],
            )
            with self.assertRaisesRegex(ValueError, "human or manual merge checkpoint"):
                merge_report(self.workspace, report)

    def test_stale_report_marks_task_for_rework_without_merging_content(self) -> None:
        self.add_task(task_record("T-001"))
        state, packet = self.run_task("T-001")
        candidate = deepcopy(state)
        candidate["glossary"]["construct"] = "A materially changed shared definition"
        self.commit(candidate, "change semantic context")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        result = merge_report(self.workspace, report)
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual(result["status"], "stale")
        self.assertEqual(state["tasks"][0]["status"], "needs_rework")
        self.assertEqual(state["evidence"], [])

    def test_relevant_route_change_rejects_the_report(self) -> None:
        state = load_state(self.workspace / "research_state.json")
        candidate = deepcopy(state)
        candidate["routes"].append({
            "id": "RT-001",
            "epistemic_goal": "explanatory",
            "method_family": "Initial project-defined method",
            "required_capabilities": ["Inspected source material"],
            "executor_mix": ["agent", "human"],
            "validation_strategy": "Compare bounded observations with alternatives",
            "uncertainty_ids": [],
            "risks": ["Source coverage may be incomplete"],
            "status": "candidate",
        })
        task = task_record("T-001")
        task["input_snapshot"]["route_ids"] = ["RT-001"]
        candidate["tasks"].append(task)
        self.commit(candidate, "add route-bound task")
        state, packet = self.run_task("T-001")
        candidate = deepcopy(state)
        candidate["routes"][0]["method_family"] = "Materially revised project method"
        self.commit(candidate, "revise the relevant route")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        result = merge_report(self.workspace, report)
        self.assertEqual(result["status"], "stale")

    def test_source_lineage_deduplicates_same_report_evidence(self) -> None:
        self.add_task(task_record("T-001"))
        state, packet = self.run_task("T-001")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        merge_report(self.workspace, report)

        state = load_state(self.workspace / "research_state.json")
        candidate = deepcopy(state)
        second = task_record("T-002")
        candidate["tasks"].append(second)
        self.commit(candidate, "add second source task")
        state, packet = self.run_task("T-002")
        duplicate = completed_report("T-002", packet["context_hash"], packet["research_revision"])
        merge_report(self.workspace, duplicate)
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual(len(state["evidence"]), 1)

    def test_opposite_evidence_is_preserved_as_conflict(self) -> None:
        self.add_task(task_record("T-001"))
        state, packet = self.run_task("T-001")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        merge_report(self.workspace, report)

        state = load_state(self.workspace / "research_state.json")
        candidate = deepcopy(state)
        candidate["tasks"].append(task_record("T-002"))
        self.commit(candidate, "add conflicting source task")
        state, packet = self.run_task("T-002")
        opposite = completed_report("T-002", packet["context_hash"], packet["research_revision"])
        opposite["evidence_candidates"][0]["stance"] = "contradicts"
        opposite["evidence_candidates"][0]["source_id"] = "doi:10.example/other"
        opposite["evidence_candidates"][0]["source_lineage"] = "doi:10.example/other"
        merge_report(self.workspace, opposite)
        state = load_state(self.workspace / "research_state.json")
        self.assertEqual(len(state["evidence"]), 2)
        self.assertEqual(state["conflicts"][0]["record_ids"], ["E-001", "E-002"])

    def test_artifact_hash_must_match_task_local_file(self) -> None:
        self.add_task(task_record("T-001"))
        state, packet = self.run_task("T-001")
        artifact_path = self.workspace / "orchestration/tasks/T-001/result.txt"
        artifact_path.write_text("raw observation", encoding="utf-8")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        report["artifacts"] = [
            {
                "id": "T-001:AR-1",
                "path": "orchestration/tasks/T-001/result.txt",
                "sha256": "0" * 64,
                "media_type": "text/plain",
                "description": "Raw observation",
                "provenance": "Produced by the bounded task",
            }
        ]
        errors = validate_report(self.workspace, report)
        self.assertTrue(any("does not match" in error for error in errors))
        report["artifacts"][0]["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        self.assertEqual(validate_report(self.workspace, report), [])

    def test_report_rejects_unknown_candidate_references(self) -> None:
        self.add_task(task_record("T-001", may_propose_claims=True))
        state, packet = self.run_task("T-001")
        report = completed_report("T-001", packet["context_hash"], packet["research_revision"])
        report["claim_candidates"] = [{
            "id": "T-001:C-1",
            "statement": "An ungrounded candidate",
            "evidence_ids": ["T-001:E-missing"],
            "observation_ids": [],
            "caveats": ["Reference must be resolvable"],
        }]
        self.assertTrue(any("unknown evidence" in error for error in validate_report(self.workspace, report)))

    def test_failed_bundle_replacement_leaves_no_partial_commit(self) -> None:
        state_path = self.workspace / "research_state.json"
        tracked = {
            path: path.read_bytes()
            for path in (
                state_path,
                self.workspace / "evidence.jsonl",
                self.workspace / "decisions.jsonl",
                self.workspace / "research_summary.md",
            )
        }
        candidate = deepcopy(load_state(state_path))
        candidate["stop_conditions"].append("A transaction failure must roll back")
        real_replace = Path.replace
        calls = {"count": 0}

        def fail_once(path: Path, target: Path) -> Path:
            calls["count"] += 1
            if calls["count"] == 3:
                raise OSError("injected replacement failure")
            return real_replace(path, target)

        with patch.object(Path, "replace", fail_once):
            with self.assertRaisesRegex(OSError, "injected"):
                self.commit(candidate, "exercise transaction rollback")
        for path, original in tracked.items():
            self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.workspace / ".checkpoints" / "research_state.r0000.json").exists())
        self.assertEqual(validate_workspace(self.workspace), [])


if __name__ == "__main__":
    unittest.main()
