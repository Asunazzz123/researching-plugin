#!/usr/bin/env python3
"""Dependency-free state, gate, checkpoint, and rendering helpers."""

from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
STAGES = (
    "framing",
    "grounding",
    "hypothesizing",
    "designing",
    "pilot_ready",
    "piloting",
    "interpreting",
    "deciding",
    "full_experiment_ready",
    "experimenting",
    "claim_review",
    "complete",
)
ALLOWED_TRANSITIONS = {
    "framing": {"framing", "grounding"},
    "grounding": {"framing", "grounding", "hypothesizing", "deciding"},
    "hypothesizing": {"grounding", "hypothesizing", "designing", "deciding"},
    "designing": {"hypothesizing", "designing", "pilot_ready", "deciding"},
    "pilot_ready": {"designing", "pilot_ready", "piloting"},
    "piloting": {"piloting", "interpreting"},
    "interpreting": {"interpreting", "deciding"},
    "deciding": {
        "grounding",
        "hypothesizing",
        "designing",
        "pilot_ready",
        "deciding",
        "full_experiment_ready",
        "claim_review",
        "complete",
    },
    "full_experiment_ready": {
        "designing",
        "full_experiment_ready",
        "experimenting",
    },
    "experimenting": {"experimenting", "interpreting"},
    "claim_review": {
        "grounding",
        "hypothesizing",
        "designing",
        "claim_review",
        "complete",
    },
    "complete": {"complete"},
}

COLLECTION_PREFIXES = {
    "uncertainties": "U",
    "evidence": "E",
    "claims": "C",
    "hypotheses": "H",
    "experiments": "EXP",
    "results": "R",
    "open_evidence_gaps": "G",
    "next_actions": "A",
}
LEGACY_APPROVAL_NAMES = ("scope", "experiment", "claim")
APPROVAL_NAMES = ("scope", "direction", "plan", "execution", "claim")
ALL_APPROVAL_NAMES = set(APPROVAL_NAMES) | set(LEGACY_APPROVAL_NAMES)
APPROVAL_DISPLAY_ORDER = ("scope", "direction", "plan", "experiment", "execution", "claim")
APPROVAL_STATUSES = {"pending", "approved", "rejected"}
EVIDENCE_STANCES = {"supports", "contradicts", "context", "inconclusive"}
SOURCE_KINDS = {"literature", "experiment", "observation", "dataset"}
SOURCE_DEPTHS = {
    "metadata",
    "abstract",
    "full_text",
    "experiment_artifact",
    "direct_observation",
    "dataset",
}
CLAIM_STATUSES = {"hypothesis", "inference", "supported", "refuted", "unknown"}
HYPOTHESIS_STATUSES = {
    "proposed",
    "active",
    "deprioritized",
    "supported",
    "refuted",
}
EXPERIMENT_STATUSES = {
    "proposed",
    "planned",
    "approved",
    "running",
    "completed",
    "failed",
    "stopped",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_project_id(question: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", question.casefold())[:6]
    slug = "-".join(words) or "research-project"
    return slug[:64]


def pending_approval() -> dict[str, Any]:
    return {"status": "pending", "by": None, "at": None, "note": None}


def initial_state(
    question: str,
    *,
    project_id: str | None = None,
    scope: Iterable[str] = (),
    non_goals: Iterable[str] = (),
    constraints: Iterable[str] = (),
    resources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("question must not be empty")
    now = utc_now()
    state = {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "created_at": now,
        "updated_at": now,
        "project": {
            "id": (project_id or make_project_id(question)).strip(),
            "question": question,
            "scope": _clean_strings(scope),
            "non_goals": _clean_strings(non_goals),
            "constraints": _clean_strings(constraints),
            "resources": resources or {},
        },
        "current_stage": "framing",
        "uncertainties": [],
        "evidence": [],
        "claims": [],
        "hypotheses": [],
        "experiments": [],
        "results": [],
        "open_evidence_gaps": [],
        "next_actions": [],
        "approvals": {name: pending_approval() for name in APPROVAL_NAMES},
        "stop_conditions": [],
    }
    errors = validation_errors(state)
    if errors:
        raise ValueError("invalid initial state: " + "; ".join(errors))
    return state


def validation_errors(
    state: Any,
    *,
    previous: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["state must be a JSON object"]

    required = {
        "schema_version",
        "revision",
        "created_at",
        "updated_at",
        "project",
        "current_stage",
        *COLLECTION_PREFIXES,
        "approvals",
        "stop_conditions",
    }
    missing = sorted(required - state.keys())
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")
        return errors

    if state["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if not isinstance(state["revision"], int) or state["revision"] < 0:
        errors.append("revision must be a non-negative integer")
    _validate_timestamp(state.get("created_at"), "created_at", errors)
    _validate_timestamp(state.get("updated_at"), "updated_at", errors)
    _validate_project(state.get("project"), errors)

    stage = state.get("current_stage")
    if stage not in STAGES:
        errors.append(f"current_stage must be one of: {', '.join(STAGES)}")

    records_by_collection: dict[str, dict[str, dict[str, Any]]] = {}
    for name, prefix in COLLECTION_PREFIXES.items():
        records_by_collection[name] = _validate_collection(
            state.get(name), name, prefix, errors
        )

    _validate_approvals(state.get("approvals"), errors)
    _validate_string_list(state.get("stop_conditions"), "stop_conditions", errors)
    _validate_evidence(records_by_collection["evidence"], errors)
    _validate_references(records_by_collection, errors)
    _validate_record_shapes(records_by_collection, errors)

    if previous is not None:
        _validate_update_invariants(previous, state, errors)

    _validate_gates(state, records_by_collection, errors)
    return errors


def validate_or_raise(
    state: Any,
    *,
    previous: dict[str, Any] | None = None,
) -> None:
    errors = validation_errors(state, previous=previous)
    if errors:
        raise ValueError("\n".join(f"- {error}" for error in errors))


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def append_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"JSONL entry at {path}:{line_number} is not an object")
            values.append(value)
    return values


def create_workspace(workspace: Path, state: dict[str, Any]) -> None:
    if workspace.exists() and any(workspace.iterdir()):
        raise FileExistsError(f"workspace is not empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / ".checkpoints").mkdir()
    (workspace / "experiments").mkdir()
    atomic_write_json(workspace / "research_state.json", state)
    (workspace / "evidence.jsonl").touch()
    (workspace / "decisions.jsonl").touch()
    write_summary(workspace, state)


def validate_workspace(workspace: Path) -> list[str]:
    errors: list[str] = []
    state_path = workspace / "research_state.json"
    if not state_path.is_file():
        return [f"missing {state_path}"]
    try:
        state = load_json(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    errors.extend(validation_errors(state))

    try:
        evidence_log = load_jsonl(workspace / "evidence.jsonl")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    else:
        if evidence_log != state.get("evidence"):
            errors.append("evidence.jsonl must exactly match the append-only evidence list")

    try:
        decisions = load_jsonl(workspace / "decisions.jsonl")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    else:
        revisions = [decision.get("revision") for decision in decisions]
        if revisions != sorted(revisions) or len(revisions) != len(set(revisions)):
            errors.append("decision revisions must be unique and monotonically increasing")
        if decisions and decisions[-1].get("revision") != state.get("revision"):
            errors.append("latest decision revision must match research_state.json")
        if not decisions and state.get("revision") != 0:
            errors.append("non-zero state revision requires a decision log entry")
    return errors


def update_workspace(
    workspace: Path,
    candidate: dict[str, Any],
    *,
    action: str,
    rationale: str,
    actor: str,
    evidence_ids: Iterable[str] = (),
) -> dict[str, Any]:
    state_path = workspace / "research_state.json"
    current = load_json(state_path)
    candidate = deepcopy(candidate)

    if candidate.get("revision") != current.get("revision"):
        raise ValueError("candidate revision is stale; reload research_state.json")
    if candidate.get("created_at") != current.get("created_at"):
        raise ValueError("created_at is immutable")
    if candidate.get("project", {}).get("id") != current.get("project", {}).get("id"):
        raise ValueError("project.id is immutable")
    validate_or_raise(candidate, previous=current)

    logged_evidence = load_jsonl(workspace / "evidence.jsonl")
    if logged_evidence != current["evidence"]:
        raise ValueError("evidence log drift detected; validate the workspace first")

    action = action.strip()
    rationale = rationale.strip()
    actor = actor.strip()
    if not action or not rationale or not actor:
        raise ValueError("action, rationale, and actor must not be empty")
    evidence_ids = tuple(dict.fromkeys(item.strip() for item in evidence_ids if item.strip()))
    known_evidence = {item["id"] for item in candidate["evidence"]}
    unknown = sorted(set(evidence_ids) - known_evidence)
    if unknown:
        raise ValueError(f"decision references unknown evidence: {', '.join(unknown)}")

    next_revision = current["revision"] + 1
    candidate["revision"] = next_revision
    candidate["updated_at"] = utc_now()
    validate_or_raise(candidate, previous=current)

    checkpoint = workspace / ".checkpoints" / f"research_state.r{current['revision']:04d}.json"
    if checkpoint.exists():
        raise FileExistsError(f"checkpoint already exists: {checkpoint}")
    atomic_write_json(checkpoint, current)

    new_evidence = candidate["evidence"][len(current["evidence"]) :]
    if new_evidence:
        append_jsonl(workspace / "evidence.jsonl", new_evidence)

    decision = {
        "timestamp": candidate["updated_at"],
        "revision": next_revision,
        "actor": actor,
        "action": action,
        "rationale": rationale,
        "stage_from": current["current_stage"],
        "stage_to": candidate["current_stage"],
        "evidence_ids": list(evidence_ids),
    }
    append_jsonl(workspace / "decisions.jsonl", [decision])
    atomic_write_json(state_path, candidate)
    write_summary(workspace, candidate)
    return decision


def render_summary(state: dict[str, Any]) -> str:
    approvals = state["approvals"]
    lines = [
        f"# Research Summary: {state['project']['id']}",
        "",
        f"- Revision: {state['revision']}",
        f"- Stage: `{state['current_stage']}`",
        f"- Updated: {state['updated_at']}",
        "",
        "## Research question",
        "",
        state["project"]["question"],
        "",
        "## Scope",
        "",
        *_render_bullets(state["project"]["scope"]),
        "",
        "## Gates",
        "",
        "| Gate | Status | Approved by |",
        "|---|---|---|",
    ]
    for name in APPROVAL_DISPLAY_ORDER:
        if name not in approvals:
            continue
        approval = approvals[name]
        lines.append(
            f"| {name} | {approval['status']} | {approval.get('by') or '-'} |"
        )

    sections = (
        ("Open uncertainties", state["uncertainties"], "question"),
        ("Evidence", state["evidence"], "proposition"),
        ("Hypotheses", state["hypotheses"], "statement"),
        ("Experiments", state["experiments"], "title"),
        ("Claims", state["claims"], "statement"),
        ("Evidence gaps", state["open_evidence_gaps"], "question"),
        ("Next actions", state["next_actions"], "action"),
    )
    for title, records, text_key in sections:
        lines.extend(("", f"## {title}", ""))
        if not records:
            lines.append("- None recorded.")
            continue
        for record in records:
            status = record.get("status")
            suffix = f" [{status}]" if status else ""
            lines.append(f"- `{record['id']}`{suffix}: {record.get(text_key, '')}")
    lines.append("")
    return "\n".join(lines)


def write_summary(workspace: Path, state: dict[str, Any]) -> None:
    path = workspace / "research_summary.md"
    content = render_summary(state)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    temporary.replace(path)


def _clean_strings(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _validate_timestamp(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{field} must be an ISO-8601 string")
        return
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an ISO-8601 string")


def _validate_project(project: Any, errors: list[str]) -> None:
    if not isinstance(project, dict):
        errors.append("project must be an object")
        return
    required = {"id", "question", "scope", "non_goals", "constraints", "resources"}
    missing = sorted(required - project.keys())
    if missing:
        errors.append(f"project missing fields: {', '.join(missing)}")
        return
    for field in ("id", "question"):
        if not isinstance(project[field], str) or not project[field].strip():
            errors.append(f"project.{field} must be a non-empty string")
    for field in ("scope", "non_goals", "constraints"):
        _validate_string_list(project[field], f"project.{field}", errors)
    if not isinstance(project["resources"], dict):
        errors.append("project.resources must be an object")


def _validate_string_list(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        errors.append(f"{field} must be a list of non-empty strings")


def _validate_collection(
    value: Any,
    name: str,
    prefix: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{name} must be a list")
        return {}
    records: dict[str, dict[str, Any]] = {}
    pattern = re.compile(rf"^{re.escape(prefix)}-[A-Za-z0-9][A-Za-z0-9._-]*$")
    for index, record in enumerate(value):
        if not isinstance(record, dict):
            errors.append(f"{name}[{index}] must be an object")
            continue
        record_id = record.get("id")
        if not isinstance(record_id, str) or not pattern.fullmatch(record_id):
            errors.append(f"{name}[{index}].id must match {prefix}-<identifier>")
            continue
        if record_id in records:
            errors.append(f"duplicate {name} id: {record_id}")
        records[record_id] = record
    return records


def _validate_approvals(value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("approvals must be an object")
        return
    names = set(value)
    missing = {"scope", "claim"} - names
    if not ({"plan", "experiment"} & names):
        missing.add("plan-or-legacy-experiment")
    unknown = names - ALL_APPROVAL_NAMES
    if missing or unknown:
        if missing:
            errors.append(f"approvals missing required gates: {', '.join(sorted(missing))}")
        if unknown:
            errors.append(f"approvals contains unknown gates: {', '.join(sorted(unknown))}")
        return
    for name in value:
        approval = value[name]
        if not isinstance(approval, dict):
            errors.append(f"approvals.{name} must be an object")
            continue
        if approval.get("status") not in APPROVAL_STATUSES:
            errors.append(f"approvals.{name}.status is invalid")
        if approval.get("status") == "approved":
            if not isinstance(approval.get("by"), str) or not approval["by"].strip():
                errors.append(f"approvals.{name}.by is required when approved")
            _validate_timestamp(approval.get("at"), f"approvals.{name}.at", errors)
            if name in {"direction", "execution"} and not _nonempty(
                approval.get("note")
            ):
                errors.append(
                    f"approvals.{name}.note must identify the selected route or authorized action"
                )


def _validate_evidence(
    evidence: dict[str, dict[str, Any]], errors: list[str]
) -> None:
    required = {
        "id",
        "proposition",
        "stance",
        "source_kind",
        "source_id",
        "source_depth",
        "locator",
        "limitations",
        "confidence",
    }
    for record_id, record in evidence.items():
        missing = sorted(required - record.keys())
        if missing:
            errors.append(f"{record_id} missing fields: {', '.join(missing)}")
            continue
        for field in ("proposition", "source_id"):
            if not isinstance(record[field], str) or not record[field].strip():
                errors.append(f"{record_id}.{field} must be a non-empty string")
        if record["stance"] not in EVIDENCE_STANCES:
            errors.append(f"{record_id}.stance is invalid")
        if record["source_kind"] not in SOURCE_KINDS:
            errors.append(f"{record_id}.source_kind is invalid")
        if record["source_depth"] not in SOURCE_DEPTHS:
            errors.append(f"{record_id}.source_depth is invalid")
        if not isinstance(record["locator"], dict):
            errors.append(f"{record_id}.locator must be an object")
        if record["source_depth"] == "full_text" and not record["locator"]:
            errors.append(f"{record_id}.locator is required for full_text evidence")
        if record["source_depth"] == "metadata" and record["stance"] not in {
            "context",
            "inconclusive",
        }:
            errors.append(f"{record_id}: metadata cannot support or contradict a claim")
        _validate_string_list(record["limitations"], f"{record_id}.limitations", errors)
        confidence = record["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            errors.append(f"{record_id}.confidence must be a number")
        elif not 0 <= confidence <= 1:
            errors.append(f"{record_id}.confidence must be between 0 and 1")


def _validate_references(
    records: dict[str, dict[str, dict[str, Any]]], errors: list[str]
) -> None:
    evidence_ids = set(records["evidence"])
    hypothesis_ids = set(records["hypotheses"])
    experiment_ids = set(records["experiments"])
    result_ids = set(records["results"])

    for collection in ("claims", "hypotheses"):
        for record_id, record in records[collection].items():
            _check_refs(record, "evidence_ids", evidence_ids, record_id, errors)
    for record_id, record in records["claims"].items():
        _check_refs(record, "result_ids", result_ids, record_id, errors)
    for record_id, record in records["experiments"].items():
        _check_refs(record, "hypothesis_ids", hypothesis_ids, record_id, errors)
    for record_id, record in records["results"].items():
        experiment_id = record.get("experiment_id")
        if experiment_id not in experiment_ids:
            errors.append(f"{record_id}.experiment_id references unknown experiment")


def _check_refs(
    record: dict[str, Any],
    field: str,
    known: set[str],
    record_id: str,
    errors: list[str],
) -> None:
    value = record.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{record_id}.{field} must be a list of ids")
        return
    unknown = sorted(set(value) - known)
    if unknown:
        errors.append(f"{record_id}.{field} references unknown ids: {', '.join(unknown)}")


def _validate_record_shapes(
    records: dict[str, dict[str, dict[str, Any]]], errors: list[str]
) -> None:
    for record_id, record in records["claims"].items():
        if not _nonempty(record.get("statement")):
            errors.append(f"{record_id}.statement must be a non-empty string")
        if record.get("status") not in CLAIM_STATUSES:
            errors.append(f"{record_id}.status is invalid")
        if record.get("status") in {"inference", "supported", "refuted"} and not (
            record.get("evidence_ids") or record.get("result_ids")
        ):
            errors.append(
                f"{record_id}: inference/supported/refuted claims need evidence or results"
            )

    for record_id, record in records["hypotheses"].items():
        if not _nonempty(record.get("statement")):
            errors.append(f"{record_id}.statement must be a non-empty string")
        if record.get("status") not in HYPOTHESIS_STATUSES:
            errors.append(f"{record_id}.status is invalid")

    for record_id, record in records["experiments"].items():
        if not _nonempty(record.get("title")):
            errors.append(f"{record_id}.title must be a non-empty string")
        if record.get("status") not in EXPERIMENT_STATUSES:
            errors.append(f"{record_id}.status is invalid")

    for record_id, record in records["results"].items():
        if not isinstance(record.get("observations"), list):
            errors.append(f"{record_id}.observations must be a list")
        if not isinstance(record.get("metrics"), dict):
            errors.append(f"{record_id}.metrics must be an object")
        _validate_string_list(
            record.get("artifact_paths"), f"{record_id}.artifact_paths", errors
        )

    for record_id, record in records["uncertainties"].items():
        if not _nonempty(record.get("question")):
            errors.append(f"{record_id}.question must be a non-empty string")
    for record_id, record in records["open_evidence_gaps"].items():
        if not _nonempty(record.get("question")):
            errors.append(f"{record_id}.question must be a non-empty string")
    for record_id, record in records["next_actions"].items():
        if not _nonempty(record.get("action")):
            errors.append(f"{record_id}.action must be a non-empty string")


def _validate_update_invariants(
    previous: dict[str, Any], candidate: dict[str, Any], errors: list[str]
) -> None:
    old_stage = previous.get("current_stage")
    new_stage = candidate.get("current_stage")
    if old_stage in ALLOWED_TRANSITIONS and new_stage not in ALLOWED_TRANSITIONS[old_stage]:
        errors.append(f"invalid stage transition: {old_stage} -> {new_stage}")
    old_evidence = previous.get("evidence", [])
    new_evidence = candidate.get("evidence", [])
    if not isinstance(new_evidence, list) or new_evidence[: len(old_evidence)] != old_evidence:
        errors.append("evidence is append-only; existing packets cannot change or disappear")
    boundary_fields = ("question", "scope", "non_goals", "constraints")
    old_project = previous.get("project", {})
    new_project = candidate.get("project", {})
    if any(old_project.get(field) != new_project.get(field) for field in boundary_fields):
        if new_stage != "framing":
            errors.append("material scope changes must return the project to framing")
        for gate in ("direction", "plan", "experiment", "execution", "claim"):
            if candidate.get("approvals", {}).get(gate, {}).get("status") == "approved":
                errors.append(f"material scope changes must reset the {gate} approval")
    if previous.get("experiments") != candidate.get("experiments"):
        plan_approval = candidate.get("approvals", {}).get(
            "plan", candidate.get("approvals", {}).get("experiment", {})
        )
        if plan_approval.get("status") == "approved":
            errors.append("plan changes must reset plan approval")
        if candidate.get("approvals", {}).get("execution", {}).get("status") == "approved":
            errors.append("plan changes must reset execution approval")


def _validate_gates(
    state: dict[str, Any],
    records: dict[str, dict[str, dict[str, Any]]],
    errors: list[str],
) -> None:
    stage = state.get("current_stage")
    approvals = state.get("approvals", {})
    project = state.get("project", {})

    if stage != "framing":
        if approvals.get("scope", {}).get("status") != "approved":
            errors.append("Scope Gate: approve scope before leaving framing")
        if not project.get("scope"):
            errors.append("Scope Gate: project.scope must not be empty")

    if stage in {
        "designing",
        "pilot_ready",
        "piloting",
        "full_experiment_ready",
        "experimenting",
    }:
        if (
            "direction" in approvals
            and approvals.get("direction", {}).get("status") != "approved"
        ):
            errors.append(
                "Direction Gate: the human must select a research route before planning"
            )
        viable = [
            item
            for item in records["hypotheses"].values()
            if item.get("status") in {"proposed", "active", "supported"}
        ]
        if not any(_hypothesis_is_testable(item) for item in viable):
            errors.append(
                "Hypothesis Gate: add a mechanistic hypothesis with predictions, "
                "falsifiers, and a cheapest discriminating test"
            )

    if stage in {
        "pilot_ready",
        "piloting",
        "full_experiment_ready",
        "experimenting",
    }:
        ready = [
            item
            for item in records["experiments"].values()
            if item.get("status") in {
                "planned",
                "approved",
                "running",
                "completed",
                "failed",
                "stopped",
            }
        ]
        if not any(_experiment_is_ready(item) for item in ready):
            errors.append("Experiment Gate: no experiment satisfies the required plan fields")
        plan_approval = approvals.get("plan", approvals.get("experiment", {}))
        if plan_approval.get("status") != "approved":
            errors.append("Plan Gate: human approval of the exact experiment plan is required")

    if stage in {"piloting", "experimenting"}:
        if (
            "execution" in approvals
            and approvals.get("execution", {}).get("status") != "approved"
        ):
            errors.append(
                "Execution Gate: explicit human authorization is required after plan approval"
            )

    if stage == "complete":
        if approvals.get("claim", {}).get("status") != "approved":
            errors.append("Claim Gate: human approval is required before completion")
        if not records["claims"]:
            errors.append("Claim Gate: record at least one bounded claim")


def _hypothesis_is_testable(record: dict[str, Any]) -> bool:
    return all(
        (
            _nonempty(record.get("statement")),
            _nonempty(record.get("mechanism")),
            _nonempty_list(record.get("predictions")),
            _nonempty_list(record.get("falsifiers")),
            _nonempty(record.get("cheapest_discriminating_test")),
        )
    )


def _experiment_is_ready(record: dict[str, Any]) -> bool:
    return all(
        (
            _nonempty_list(record.get("hypothesis_ids")),
            isinstance(record.get("variables"), dict) and bool(record["variables"]),
            _nonempty_list(record.get("baselines")),
            _nonempty_list(record.get("controls")),
            _nonempty(record.get("primary_metric")),
            isinstance(record.get("budget"), dict) and bool(record["budget"]),
            _nonempty_list(record.get("stop_conditions")),
        )
    )


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _render_bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] or ["- Not yet approved."]
