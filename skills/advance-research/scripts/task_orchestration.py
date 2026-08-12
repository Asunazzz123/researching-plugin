#!/usr/bin/env python3
"""Task-DAG frontier, context, report, handoff, and single-writer reducer."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

from research_state import (
    CANONICAL_WRITER,
    CONFLICT_SEVERITIES,
    EVIDENCE_STANCES,
    SCHEMA_VERSION,
    SOURCE_DEPTHS,
    SOURCE_KINDS,
    atomic_write_json,
    load_json,
    load_state,
    update_workspace,
    validate_or_raise,
)


REPORT_STATUSES = {"completed", "partial", "blocked", "failed"}
AUTO_LEVELS = {"H0", "H1"}
ALLOWED_AUTO_MODES = {"read_only", "prepare", "execute_reversible"}
SAFE_AUTO_SIDE_EFFECTS = {"none", "local_write"}
REPORT_KEYS = {
    "report_id", "task_id", "based_on_revision", "context_hash", "status",
    "actions", "observations", "evidence_candidates", "claim_candidates",
    "contradictions", "unknowns", "limitations", "artifacts",
    "recommended_next_actions",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _by_id(state: dict[str, Any], collection: str) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in state[collection]}


def get_task(state: dict[str, Any], task_id: str) -> dict[str, Any]:
    task = _by_id(state, "tasks").get(task_id)
    if task is None:
        raise ValueError(f"unknown task_id: {task_id}")
    return task


def context_payload(state: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    snapshot = task.get("input_snapshot", {})
    relevant = {}
    for collection, field in (
        ("routes", "route_ids"),
        ("protocols", "protocol_ids"),
        ("uncertainties", "uncertainty_ids"),
        ("evidence", "evidence_ids"),
        ("claims", "claim_ids"),
        ("artifacts", "artifact_ids"),
    ):
        ids = task.get(field, []) if field == "uncertainty_ids" else snapshot.get(field, [])
        if collection in {"routes", "protocols"} and not ids:
            continue
        index = _by_id(state, collection)
        relevant[collection] = [index[item_id] for item_id in ids if item_id in index]
    immutable_task = {
        key: deepcopy(task.get(key))
        for key in (
            "id", "parent_task_id", "title", "task_kind", "epistemic_role",
            "question", "uncertainty_ids", "human_level", "executor", "depends_on",
            "priority", "execution", "output_contract", "validation", "merge",
            "human_handoff",
        )
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "project": {
            key: deepcopy(state["project"][key])
            for key in ("question", "scope", "non_goals", "constraints")
        },
        "glossary": deepcopy(state["glossary"]),
        "task": immutable_task,
        "relevant_records": relevant,
    }


def task_context_hash(state: dict[str, Any], task: dict[str, Any]) -> str:
    return _sha256_json(context_payload(state, task))


def build_context_packet(state: dict[str, Any], task_id: str) -> dict[str, Any]:
    validate_or_raise(state)
    task = get_task(state, task_id)
    payload = context_payload(state, task)
    context_hash = _sha256_json(payload)
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "research_revision": state["revision"],
        "context_hash": context_hash,
        **payload,
        "report_contract": {
            "required_top_level": sorted(REPORT_KEYS),
            "allowed_status": sorted(REPORT_STATUSES),
            "report_id_pattern": f"REP-{task_id}-<identifier>",
            "based_on_revision": state["revision"],
            "temporary_id_namespace": f"{task_id}:<kind>-<identifier>",
            "actions": "Array of action/outcome records or concise strings.",
            "unknowns": "Array of non-empty strings.",
            "limitations": "Array of non-empty strings.",
            "recommended_next_actions": "Array; recommendations do not authorize execution.",
            "observation": {
                "required": ["id", "description", "protocol_ids", "artifact_ids", "limitations"],
                "id_kind": "O",
                "types": {
                    "description": "non-empty string",
                    "protocol_ids": "array of canonical PR-* ids",
                    "artifact_ids": "array of canonical AR-* or task-local AR ids",
                    "limitations": "array of non-empty strings",
                },
            },
            "evidence_candidate": {
                "required": [
                    "id", "proposition", "stance", "source_kind", "source_id",
                    "source_lineage", "source_depth", "locator", "limitations", "confidence",
                ],
                "id_kind": "E",
                "types": {
                    "proposition": "non-empty string",
                    "stance": sorted(EVIDENCE_STANCES),
                    "source_kind": sorted(SOURCE_KINDS),
                    "source_id": "non-empty string",
                    "source_lineage": "one stable non-empty string, not an array",
                    "source_depth": sorted(SOURCE_DEPTHS),
                    "locator": "JSON object; required and non-empty for inspected evidence",
                    "limitations": "array of non-empty strings",
                    "confidence": "number from 0 to 1",
                },
            },
            "claim_candidate": {
                "required": ["id", "statement", "evidence_ids", "observation_ids", "caveats"],
                "id_kind": "C",
                "canonical_status": "candidate",
                "types": {
                    "evidence_ids": "array of canonical or task-local E ids",
                    "observation_ids": "array of canonical or task-local O ids",
                    "caveats": "array of non-empty strings",
                },
            },
            "contradiction": {
                "required": ["id", "statement", "record_ids"],
                "optional": ["severity"],
                "id_kind": "CF",
                "allowed_severity": sorted(CONFLICT_SEVERITIES),
            },
            "artifact": {
                "required": ["id", "path", "sha256", "media_type", "description", "provenance"],
                "id_kind": "AR",
                "boundary": (
                    "List only files newly produced by this task. Use a task-local AR id and a path "
                    f"under {task['execution']['write_scope']}/. Do not copy referenced input artifacts here."
                ),
            },
        },
        "prohibitions": [
            "Do not spawn another sub-agent.",
            "Do not edit research_state.json, evidence.jsonl, decisions.jsonl, or approvals.",
            "Do not read workspace files outside this Context Packet and task.execution.read_scope.",
            f"Do not write outside {task['execution']['write_scope']}.",
            "Do not mark a candidate claim as accepted or scientifically true.",
        ],
    }


def prepare_task_context(workspace: Path, task_id: str) -> dict[str, Any]:
    workspace = workspace.resolve()
    state = load_state(workspace / "research_state.json")
    task = get_task(state, task_id)
    if task["status"] not in {"draft", "needs_rework", "blocked"}:
        raise ValueError(f"{task_id} cannot be prepared from status {task['status']!r}")
    packet = build_context_packet(state, task_id)
    candidate = deepcopy(state)
    candidate_task = get_task(candidate, task_id)
    candidate_task["input_snapshot"]["research_revision"] = state["revision"]
    candidate_task["input_snapshot"]["context_hash"] = packet["context_hash"]
    candidate_task["status"] = "waiting_human" if candidate_task["human_level"] in {"H3", "H4"} else "ready"

    context_path = workspace / candidate_task["execution"]["write_scope"] / "context.json"
    packet_bytes = (json.dumps(packet, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    decision = update_workspace(
        workspace,
        candidate,
        action=f"prepare context for {task_id}",
        rationale="freeze the minimum task-local context before dispatch or human handoff",
        actor=CANONICAL_WRITER,
        extra_files=((context_path, packet_bytes),),
    )
    packet["prepared_by_revision"] = decision["revision"]
    return {"context_path": str(context_path), "packet": packet, "decision": decision}


def _gate_ready(state: dict[str, Any], task: dict[str, Any]) -> tuple[bool, str | None]:
    gate = task["merge"].get("required_gate")
    if gate and state["approvals"][gate]["status"] != "approved":
        return False, f"waiting for {gate} gate"
    if task["execution"]["mode"] == "execute_external":
        return False, "external execution is never auto-dispatched"
    if task["execution"]["mode"] not in ALLOWED_AUTO_MODES:
        return False, "execution mode is not session-auto-dispatchable"
    unsafe = sorted(set(task["execution"]["side_effects"]) - SAFE_AUTO_SIDE_EFFECTS)
    if unsafe:
        return False, "unsafe side effects: " + ", ".join(unsafe)
    return True, None


def ready_frontier(state: dict[str, Any], max_parallel: int = 3) -> dict[str, Any]:
    validate_or_raise(state)
    if not isinstance(max_parallel, int) or max_parallel < 1:
        raise ValueError("max_parallel must be a positive integer")
    max_parallel = min(max_parallel, 3)
    tasks = _by_id(state, "tasks")
    active_locks = {
        lock
        for task in tasks.values()
        if task["status"] in {"assigned", "running"}
        for lock in task["execution"]["resource_locks"]
    }
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, str]] = []
    claimed_locks = set(active_locks)
    candidates = sorted(
        (task for task in tasks.values() if task["status"] == "ready"),
        key=lambda item: (-item["priority"], item["id"]),
    )
    for task in candidates:
        reasons: list[str] = []
        incomplete = [dep for dep in task["depends_on"] if tasks[dep]["status"] != "merged"]
        if incomplete:
            reasons.append("incomplete dependencies: " + ", ".join(incomplete))
        expected_hash = task_context_hash(state, task)
        if task["input_snapshot"].get("context_hash") != expected_hash:
            reasons.append("stale context hash")
        gate_ok, gate_reason = _gate_ready(state, task)
        if not gate_ok and gate_reason:
            reasons.append(gate_reason)
        if task["human_level"] in {"H3", "H4"}:
            reasons.append("requires human participation")
        elif task["human_level"] == "H2" and task["merge"]["strategy"] != "human_checkpoint":
            reasons.append("H2 sub-agent work must merge through a human checkpoint")
        locks = set(task["execution"]["resource_locks"])
        if locks & claimed_locks:
            reasons.append("resource lock conflict: " + ", ".join(sorted(locks & claimed_locks)))
        if task["executor"] != "subagent":
            reasons.append(f"executor is {task['executor']}, not subagent")
        if len(selected) >= max_parallel:
            reasons.append("parallel limit reached")
        if reasons:
            deferred.append({"task_id": task["id"], "reason": "; ".join(reasons)})
            continue
        selected.append({
            "task_id": task["id"],
            "human_level": task["human_level"],
            "dispatch_mode": "candidate_only" if task["human_level"] == "H2" else "auto_validated",
            "parallel_group": task["execution"].get("parallel_group"),
            "write_scope": task["execution"]["write_scope"],
            "context_hash": expected_hash,
        })
        claimed_locks.update(locks)
    return {"max_parallel": max_parallel, "selected": selected, "deferred": deferred}


def start_tasks(workspace: Path, task_ids: list[str]) -> dict[str, Any]:
    workspace = workspace.resolve()
    task_ids = list(dict.fromkeys(task_ids))
    if not task_ids:
        raise ValueError("at least one task_id is required")
    state = load_state(workspace / "research_state.json")
    frontier = ready_frontier(state, max_parallel=len(task_ids))
    selected = {item["task_id"] for item in frontier["selected"]}
    unavailable = sorted(set(task_ids) - selected)
    if unavailable:
        raise ValueError("tasks are not in the dispatchable frontier: " + ", ".join(unavailable))
    candidate = deepcopy(state)
    task_index = _by_id(candidate, "tasks")
    for task_id in task_ids:
        task_index[task_id]["status"] = "running"
    decision = update_workspace(
        workspace,
        candidate,
        action="start task batch " + ", ".join(task_ids),
        rationale="dispatch a validated non-conflicting session-local frontier",
        actor=CANONICAL_WRITER,
    )
    return {"status": "running", "task_ids": task_ids, "decision": decision}


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def _temporary_id(value: Any, task_id: str, kind: str) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(rf"{re.escape(task_id)}:{kind}-[A-Za-z0-9][A-Za-z0-9._-]*", value))


def validate_report(workspace: Path, report: dict[str, Any]) -> list[str]:
    workspace = workspace.resolve()
    errors: list[str] = []
    if not isinstance(report, dict):
        return ["report must be an object"]
    missing, unknown = REPORT_KEYS - report.keys(), report.keys() - REPORT_KEYS
    if missing:
        errors.append("report missing fields: " + ", ".join(sorted(missing)))
    if unknown:
        errors.append("report has unknown fields: " + ", ".join(sorted(unknown)))
    if missing:
        return errors
    state = load_state(workspace / "research_state.json")
    try:
        task = get_task(state, report.get("task_id"))
    except ValueError as exc:
        return errors + [str(exc)]
    task_id = task["id"]
    if not isinstance(report.get("report_id"), str) or not re.fullmatch(rf"REP-{re.escape(task_id)}-[A-Za-z0-9][A-Za-z0-9._-]*", report["report_id"]):
        errors.append(f"report_id must match REP-{task_id}-<identifier>")
    if not isinstance(report.get("based_on_revision"), int) or report["based_on_revision"] < 0:
        errors.append("based_on_revision must be a non-negative integer")
    elif report["based_on_revision"] != task.get("input_snapshot", {}).get("research_revision"):
        errors.append("based_on_revision must match the frozen task input snapshot")
    if not isinstance(report.get("context_hash"), str) or not re.fullmatch(r"[0-9a-f]{64}", report["context_hash"]):
        errors.append("context_hash must be lowercase SHA-256")
    elif report["context_hash"] != task.get("input_snapshot", {}).get("context_hash"):
        errors.append("context_hash must match the frozen task input snapshot")
    if report.get("status") not in REPORT_STATUSES:
        errors.append("report.status is invalid")
    for field in (
        "actions", "observations", "evidence_candidates", "claim_candidates",
        "contradictions", "artifacts", "recommended_next_actions",
    ):
        if not isinstance(report.get(field), list):
            errors.append(f"{field} must be a list")
    for field in ("unknowns", "limitations"):
        if not _strings(report.get(field)):
            errors.append(f"{field} must be a list of non-empty strings")
    if any(
        not isinstance(report.get(field), list)
        for field in (
            "actions", "observations", "evidence_candidates", "claim_candidates",
            "contradictions", "artifacts", "recommended_next_actions",
        )
    ):
        return errors
    if report["evidence_candidates"] and not task["output_contract"]["may_propose_evidence"]:
        errors.append(f"{task_id} may not propose evidence")
    if report["claim_candidates"] and not task["output_contract"]["may_propose_claims"]:
        errors.append(f"{task_id} may not propose claims")

    namespaces = {
        "artifacts": "AR",
        "observations": "O",
        "evidence_candidates": "E",
        "claim_candidates": "C",
        "contradictions": "CF",
    }
    report_ids: dict[str, set[str]] = {field: set() for field in namespaces}
    all_report_ids: set[str] = set()
    for field, kind in namespaces.items():
        for record in report[field]:
            record_id = record.get("id") if isinstance(record, dict) else None
            if _temporary_id(record_id, task_id, kind):
                if record_id in all_report_ids:
                    errors.append(f"duplicate task-local id: {record_id}")
                report_ids[field].add(record_id)
                all_report_ids.add(record_id)

    canonical_ids = {
        collection: set(_by_id(state, collection))
        for collection in ("artifacts", "observations", "evidence", "claims", "conflicts", "protocols")
    }
    known_temp_ids: set[str] = set()
    for artifact in report["artifacts"]:
        if not isinstance(artifact, dict) or not _temporary_id(artifact.get("id"), task_id, "AR"):
            errors.append("artifact candidate ids must use the task AR namespace")
            continue
        known_temp_ids.add(artifact["id"])
        path_value = artifact.get("path")
        if not _safe_relative_path(path_value) or not str(path_value).startswith(task["execution"]["write_scope"] + "/"):
            errors.append(f"{artifact['id']}.path must stay under the task write_scope")
            continue
        path = (workspace / path_value).resolve()
        scope_path = (workspace / task["execution"]["write_scope"]).resolve()
        if not path.is_relative_to(scope_path):
            errors.append(f"{artifact['id']}.path resolves outside the task write_scope")
            continue
        if not path.is_file():
            errors.append(f"{artifact['id']}.path does not exist")
        else:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if artifact.get("sha256") != digest:
                errors.append(f"{artifact['id']}.sha256 does not match the file")
        for field in ("media_type", "description", "provenance"):
            if not isinstance(artifact.get(field), str) or not artifact[field].strip():
                errors.append(f"{artifact['id']}.{field} must be non-empty")

    for observation in report["observations"]:
        if not isinstance(observation, dict) or not _temporary_id(observation.get("id"), task_id, "O"):
            errors.append("observation ids must use the task O namespace")
            continue
        known_temp_ids.add(observation["id"])
        if not isinstance(observation.get("description"), str) or not observation["description"].strip():
            errors.append(f"{observation['id']}.description must be non-empty")
        if not _strings(observation.get("limitations")):
            errors.append(f"{observation['id']}.limitations must be strings")
        allowed_artifacts = canonical_ids["artifacts"] | report_ids["artifacts"]
        if not isinstance(observation.get("artifact_ids"), list) or any(item not in allowed_artifacts for item in observation.get("artifact_ids", [])):
            errors.append(f"{observation['id']}.artifact_ids reference unknown report artifacts")
        if not isinstance(observation.get("protocol_ids"), list) or any(item not in canonical_ids["protocols"] for item in observation.get("protocol_ids", [])):
            errors.append(f"{observation['id']}.protocol_ids reference unknown protocols")

    for evidence in report["evidence_candidates"]:
        if not isinstance(evidence, dict) or not _temporary_id(evidence.get("id"), task_id, "E"):
            errors.append("evidence candidate ids must use the task E namespace")
            continue
        known_temp_ids.add(evidence["id"])
        required = {
            "proposition", "stance", "source_kind", "source_id", "source_lineage",
            "source_depth", "locator", "limitations", "confidence",
        }
        if required - evidence.keys():
            errors.append(f"{evidence['id']} is missing Evidence Packet fields")
        for field in ("proposition", "source_kind", "source_id", "source_lineage", "source_depth", "stance"):
            if not isinstance(evidence.get(field), str) or not evidence[field].strip():
                errors.append(f"{evidence['id']}.{field} must be non-empty")
        if not _strings(evidence.get("limitations")):
            errors.append(f"{evidence['id']}.limitations must be strings")
        confidence = evidence.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"{evidence['id']}.confidence must be between 0 and 1")
        if not isinstance(evidence.get("locator"), dict):
            errors.append(f"{evidence['id']}.locator must be an object")
        if evidence.get("source_depth") in {"full_text", "artifact", "direct_observation", "dataset", "expert_attestation"} and not evidence.get("locator"):
            errors.append(f"{evidence['id']}.locator is required for inspected evidence")
        if evidence.get("stance") not in EVIDENCE_STANCES:
            errors.append(f"{evidence['id']}.stance is invalid")
        if evidence.get("source_kind") not in SOURCE_KINDS:
            errors.append(f"{evidence['id']}.source_kind is invalid")
        if evidence.get("source_depth") not in SOURCE_DEPTHS:
            errors.append(f"{evidence['id']}.source_depth is invalid")
        if evidence.get("source_depth") == "metadata" and evidence.get("stance") not in {"context", "inconclusive"}:
            errors.append(f"{evidence['id']}: metadata cannot support or contradict")

    for claim in report["claim_candidates"]:
        if not isinstance(claim, dict) or not _temporary_id(claim.get("id"), task_id, "C"):
            errors.append("claim candidate ids must use the task C namespace")
            continue
        known_temp_ids.add(claim["id"])
        if not isinstance(claim.get("statement"), str) or not claim["statement"].strip():
            errors.append(f"{claim['id']}.statement must be non-empty")
        for field in ("evidence_ids", "observation_ids"):
            if not isinstance(claim.get(field), list):
                errors.append(f"{claim['id']}.{field} must be a list")
        allowed_evidence = canonical_ids["evidence"] | report_ids["evidence_candidates"]
        if isinstance(claim.get("evidence_ids"), list) and any(item not in allowed_evidence for item in claim["evidence_ids"]):
            errors.append(f"{claim['id']}.evidence_ids reference unknown evidence")
        allowed_observations = canonical_ids["observations"] | report_ids["observations"]
        if isinstance(claim.get("observation_ids"), list) and any(item not in allowed_observations for item in claim["observation_ids"]):
            errors.append(f"{claim['id']}.observation_ids reference unknown observations")
        if not _strings(claim.get("caveats")):
            errors.append(f"{claim['id']}.caveats must be strings")

    for conflict in report["contradictions"]:
        if not isinstance(conflict, dict) or not _temporary_id(conflict.get("id"), task_id, "CF"):
            errors.append("contradiction ids must use the task CF namespace")
            continue
        if not isinstance(conflict.get("statement"), str) or not conflict["statement"].strip():
            errors.append(f"{conflict['id']}.statement must be non-empty")
        if conflict.get("severity", "medium") not in CONFLICT_SEVERITIES:
            errors.append(f"{conflict['id']}.severity is invalid")
        if not isinstance(conflict.get("record_ids"), list) or len(conflict.get("record_ids", [])) < 2:
            errors.append(f"{conflict['id']}.record_ids must contain at least two ids")
        else:
            allowed_records = set().union(*canonical_ids.values(), all_report_ids)
            if any(item not in allowed_records for item in conflict["record_ids"]):
                errors.append(f"{conflict['id']}.record_ids reference unknown records")
    return errors


def _next_id(records: Iterable[dict[str, Any]], prefix: str) -> str:
    used = {item["id"] for item in records}
    number = 1
    while f"{prefix}-{number:03d}" in used:
        number += 1
    return f"{prefix}-{number:03d}"


def _normal(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _map_refs(values: list[str], mapping: dict[str, str]) -> list[str]:
    return list(dict.fromkeys(mapping.get(value, value) for value in values))


def merge_report(workspace: Path, report: dict[str, Any], *, actor: str = CANONICAL_WRITER) -> dict[str, Any]:
    workspace = workspace.resolve()
    if actor != CANONICAL_WRITER:
        raise ValueError("only the main agent may invoke the canonical reducer")
    errors = validate_report(workspace, report)
    if errors:
        raise ValueError("\n".join(f"- {error}" for error in errors))
    state = load_state(workspace / "research_state.json")
    task = get_task(state, report["task_id"])
    if task["human_level"] not in AUTO_LEVELS or task["merge"]["strategy"] != "append_candidates":
        raise ValueError(f"{task['id']} requires a human or manual merge checkpoint")
    if task["status"] not in {"assigned", "running", "reported", "validating"}:
        raise ValueError(f"{task['id']} cannot merge a report from status {task['status']!r}")

    report_path = workspace / "orchestration" / "reports" / f"{report['report_id']}.json"
    if report_path.exists():
        raise FileExistsError(f"report is immutable and already exists: {report_path}")
    report_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    current_hash = task_context_hash(state, task)
    if report["context_hash"] != current_hash:
        candidate = deepcopy(state)
        get_task(candidate, task["id"])["status"] = "needs_rework"
        decision = update_workspace(
            workspace, candidate,
            action=f"reject stale report {report['report_id']}",
            rationale="the task-local semantic context changed after dispatch",
            actor=actor,
            extra_files=((report_path, report_bytes),),
        )
        return {"status": "stale", "report_path": str(report_path), "decision": decision}

    if report["status"] != "completed":
        candidate = deepcopy(state)
        get_task(candidate, task["id"])["status"] = (
            "reported" if report["status"] == "partial" else "blocked"
        )
        decision = update_workspace(
            workspace, candidate,
            action=f"archive {report['status']} report {report['report_id']}",
            rationale="preserve unsuccessful or incomplete work without merging candidate content",
            actor=actor,
            extra_files=((report_path, report_bytes),),
        )
        return {
            "status": report["status"],
            "report_path": str(report_path),
            "decision": decision,
        }

    candidate = deepcopy(state)
    mapping: dict[str, str] = {}
    new_evidence_ids: list[str] = []

    for artifact in report["artifacts"]:
        existing = next((item for item in candidate["artifacts"] if item["sha256"] == artifact["sha256"]), None)
        if existing:
            mapping[artifact["id"]] = existing["id"]
            continue
        canonical_id = _next_id(candidate["artifacts"], "AR")
        mapping[artifact["id"]] = canonical_id
        candidate["artifacts"].append({
            "id": canonical_id,
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "media_type": artifact["media_type"],
            "description": artifact["description"],
            "provenance": artifact["provenance"],
            "status": "available",
        })

    for observation in report["observations"]:
        canonical_id = _next_id(candidate["observations"], "O")
        mapping[observation["id"]] = canonical_id
        candidate["observations"].append({
            "id": canonical_id,
            "task_id": task["id"],
            "protocol_ids": observation.get("protocol_ids", []),
            "description": observation["description"],
            "artifact_ids": _map_refs(observation.get("artifact_ids", []), mapping),
            "limitations": observation["limitations"],
            "status": "recorded",
        })

    for evidence in report["evidence_candidates"]:
        existing = next((
            item for item in candidate["evidence"]
            if _normal(item["proposition"]) == _normal(evidence["proposition"])
            and item["source_lineage"] == evidence["source_lineage"]
            and item["stance"] == evidence["stance"]
        ), None)
        if existing:
            mapping[evidence["id"]] = existing["id"]
            continue
        canonical_id = _next_id(candidate["evidence"], "E")
        mapping[evidence["id"]] = canonical_id
        candidate["evidence"].append({"id": canonical_id, **{key: deepcopy(value) for key, value in evidence.items() if key != "id"}})
        new_evidence_ids.append(canonical_id)
        opposites = [
            item for item in candidate["evidence"][:-1]
            if _normal(item["proposition"]) == _normal(evidence["proposition"])
            and {item["stance"], evidence["stance"]} == {"supports", "contradicts"}
        ]
        for opposite in opposites:
            conflict_id = _next_id(candidate["conflicts"], "CF")
            candidate["conflicts"].append({
                "id": conflict_id,
                "statement": f"Evidence disagrees about: {evidence['proposition']}",
                "record_ids": [opposite["id"], canonical_id],
                "severity": "high",
                "status": "open",
            })

    for claim in report["claim_candidates"]:
        canonical_id = _next_id(candidate["claims"], "C")
        mapping[claim["id"]] = canonical_id
        candidate["claims"].append({
            "id": canonical_id,
            "statement": claim["statement"],
            "status": "candidate",
            "evidence_ids": _map_refs(claim.get("evidence_ids", []), mapping),
            "observation_ids": _map_refs(claim.get("observation_ids", []), mapping),
            "caveats": claim["caveats"],
        })

    for conflict in report["contradictions"]:
        record_ids = _map_refs(conflict["record_ids"], mapping)
        if len(set(record_ids)) < 2:
            continue
        candidate["conflicts"].append({
            "id": _next_id(candidate["conflicts"], "CF"),
            "statement": conflict["statement"],
            "record_ids": record_ids,
            "severity": conflict.get("severity", "medium"),
            "status": "open",
        })

    get_task(candidate, task["id"])["status"] = "merged"
    validate_or_raise(candidate, previous=state)
    decision = update_workspace(
        workspace, candidate,
        action=f"merge report {report['report_id']}",
        rationale="validated task-local candidates through the single-writer reducer",
        actor=actor,
        evidence_ids=new_evidence_ids,
        extra_files=((report_path, report_bytes),),
    )
    return {
        "status": "merged",
        "report_path": str(report_path),
        "id_mapping": mapping,
        "decision": decision,
    }


def render_handoff(state: dict[str, Any], task_id: str) -> str:
    validate_or_raise(state)
    task = get_task(state, task_id)
    if task["human_level"] not in {"H3", "H4"}:
        raise ValueError("human handoff is only valid for H3/H4 tasks")
    handoff = task["human_handoff"]
    lines = [
        f"# Human Handoff: {task_id}", "",
        f"- Human level: `{task['human_level']}`",
        f"- Research question: {task['question']}",
        f"- Resume condition: {handoff['resume_condition']}", "",
        "## Action", "", handoff["action"], "",
    ]
    for title, field in (
        ("Prerequisites", "prerequisites"),
        ("Quality requirements", "quality_requirements"),
        ("Expected artifacts", "expected_artifacts"),
        ("Bias record", "bias_fields"),
        ("Deviation record", "deviation_fields"),
    ):
        lines.extend((f"## {title}", "", *[f"- {item}" for item in handoff[field]], ""))
    lines.extend((
        "## Return boundary", "",
        "Return observations and artifacts with provenance. They remain candidates until validated and merged by the main agent.", "",
    ))
    return "\n".join(lines)
