#!/usr/bin/env python3
"""Schema-v2 research state, gate, checkpoint, and rendering helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


SCHEMA_VERSION = "2.0"
SCHEMA_MIGRATIONS: dict[tuple[str, str], Callable[[dict[str, Any]], dict[str, Any]]] = {}

STAGES = (
    "framing",
    "grounding",
    "route_selection",
    "planning",
    "working",
    "interpreting",
    "claim_review",
    "deciding",
    "complete",
)
ALLOWED_TRANSITIONS = {
    "framing": {"framing", "grounding"},
    "grounding": {"framing", "grounding", "route_selection", "interpreting", "deciding"},
    "route_selection": {"framing", "grounding", "route_selection", "planning", "deciding"},
    "planning": {"framing", "route_selection", "planning", "working", "deciding"},
    "working": {"framing", "planning", "working", "interpreting", "deciding"},
    "interpreting": {
        "framing", "grounding", "planning", "working", "interpreting",
        "claim_review", "deciding",
    },
    "claim_review": {"framing", "grounding", "planning", "claim_review", "deciding", "complete"},
    "deciding": {
        "framing", "grounding", "route_selection", "planning", "working",
        "claim_review", "deciding", "complete",
    },
    "complete": {"framing", "grounding", "complete"},
}

COLLECTION_PREFIXES = {
    "uncertainties": "U",
    "evidence": "E",
    "claims": "C",
    "routes": "RT",
    "working_propositions": "WP",
    "protocols": "PR",
    "observations": "O",
    "tasks": "T",
    "artifacts": "AR",
    "open_evidence_gaps": "G",
    "conflicts": "CF",
}

APPROVAL_NAMES = ("scope", "direction", "plan", "execution", "claim")
APPROVAL_STATUSES = {"pending", "approved", "rejected"}
EVIDENCE_STANCES = {"supports", "contradicts", "context", "inconclusive"}
SOURCE_KINDS = {
    "literature", "observation", "dataset", "artifact", "expert", "archive", "other"
}
SOURCE_DEPTHS = {
    "metadata", "abstract", "full_text", "artifact", "direct_observation",
    "dataset", "expert_attestation",
}
CLAIM_STATUSES = {
    "candidate", "inference", "supported", "refuted", "unknown", "needs_review"
}
EPISTEMIC_GOALS = {
    "descriptive", "explanatory", "predictive", "evaluative",
    "interpretive", "design", "mixed",
}
ROUTE_STATUSES = {"candidate", "selected", "rejected", "active", "completed", "superseded"}
PROPOSITION_KINDS = {
    "hypothesis", "interpretation", "model", "design_proposition",
    "descriptive_expectation", "other",
}
PROPOSITION_STATUSES = {"proposed", "active", "deprioritized", "supported", "refuted", "unknown"}
PROTOCOL_STATUSES = {"proposed", "planned", "approved", "running", "completed", "failed", "stopped"}
OBSERVATION_STATUSES = {"recorded", "validated", "rejected"}
ARTIFACT_STATUSES = {"available", "missing", "superseded"}
CONFLICT_SEVERITIES = {"low", "medium", "high", "blocking"}
CONFLICT_STATUSES = {"open", "resolved", "accepted_boundary"}

TASK_KINDS = {
    "discover", "extract", "normalize", "analyze", "generate",
    "criticize", "plan", "execute", "synthesize", "decide",
}
HUMAN_LEVELS = ("H0", "H1", "H2", "H3", "H4")
EXECUTORS = {"main_agent", "subagent", "human", "shared", "expert", "external"}
ROUTE_EXECUTORS = {"agent", "human", "shared", "expert", "external"}
TASK_STATUSES = {
    "draft", "ready", "assigned", "running", "waiting_human", "reported",
    "validating", "needs_rework", "merged", "blocked", "cancelled", "superseded",
}
TASK_TRANSITIONS = {
    "draft": {"draft", "ready", "waiting_human", "blocked", "cancelled", "superseded"},
    "ready": {"ready", "assigned", "running", "waiting_human", "needs_rework", "blocked", "cancelled", "superseded"},
    "assigned": {"assigned", "running", "ready", "merged", "needs_rework", "blocked", "cancelled", "superseded"},
    "running": {"running", "reported", "merged", "needs_rework", "waiting_human", "blocked", "cancelled", "superseded"},
    "waiting_human": {"waiting_human", "ready", "running", "reported", "blocked", "cancelled", "superseded"},
    "reported": {"reported", "validating", "merged", "needs_rework", "blocked", "cancelled", "superseded"},
    "validating": {"validating", "merged", "needs_rework", "blocked", "cancelled", "superseded"},
    "needs_rework": {"needs_rework", "draft", "ready", "assigned", "cancelled", "superseded"},
    "blocked": {"blocked", "draft", "ready", "waiting_human", "cancelled", "superseded"},
    "merged": {"merged", "superseded"},
    "cancelled": {"cancelled"},
    "superseded": {"superseded"},
}
EXECUTION_MODES = {"read_only", "prepare", "execute_reversible", "execute_external"}
VALIDATION_MODES = {"deterministic", "schema_and_source", "independent_review", "human_review"}
MERGE_STRATEGIES = {"append_candidates", "human_checkpoint", "manual"}
GATE_NAMES = {None, *APPROVAL_NAMES}
CANONICAL_WRITER = "main-agent"


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
        "glossary": {},
        "current_stage": "framing",
        **{name: [] for name in COLLECTION_PREFIXES},
        "approvals": {name: pending_approval() for name in APPROVAL_NAMES},
        "stop_conditions": [],
    }
    validate_or_raise(state)
    return state


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_state(path: Path) -> dict[str, Any]:
    state = load_json(path)
    version = state.get("schema_version")
    if version != SCHEMA_VERSION:
        migration = SCHEMA_MIGRATIONS.get((str(version), SCHEMA_VERSION))
        if migration is not None:
            raise ValueError(
                f"schema_version {version!r} requires an explicit migration before writing"
            )
        raise ValueError(
            f"unsupported schema_version {version!r}; this release writes only {SCHEMA_VERSION!r}"
        )
    return state


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
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _jsonl_bytes(values: Iterable[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"
        for value in values
    ).encode("utf-8")


def atomic_replace_bundle(files: Iterable[tuple[Path, bytes]]) -> None:
    """Best-effort all-or-nothing replacement for one workspace transaction."""
    prepared: list[tuple[Path, Path, bytes | None]] = []
    replaced: list[tuple[Path, bytes | None]] = []
    try:
        for path, content in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            original = path.read_bytes() if path.exists() else None
            with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                temporary = Path(handle.name)
            prepared.append((path, temporary, original))
        for path, temporary, original in prepared:
            temporary.replace(path)
            replaced.append((path, original))
    except Exception:
        for path, original in reversed(replaced):
            if original is None:
                path.unlink(missing_ok=True)
            else:
                with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as handle:
                    handle.write(original)
                    handle.flush()
                    os.fsync(handle.fileno())
                    rollback = Path(handle.name)
                rollback.replace(path)
        raise
    finally:
        for _, temporary, _ in prepared:
            temporary.unlink(missing_ok=True)


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
    validate_or_raise(state)
    workspace.mkdir(parents=True, exist_ok=True)
    for directory in (
        ".checkpoints", "artifacts", "orchestration/tasks", "orchestration/reports"
    ):
        (workspace / directory).mkdir(parents=True)
    atomic_write_json(workspace / "research_state.json", state)
    (workspace / "evidence.jsonl").touch()
    (workspace / "decisions.jsonl").touch()
    write_summary(workspace, state)


def validation_errors(
    state: Any,
    *,
    previous: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["state must be a JSON object"]
    required = {
        "schema_version", "revision", "created_at", "updated_at", "project",
        "glossary", "current_stage", *COLLECTION_PREFIXES, "approvals", "stop_conditions",
    }
    missing = sorted(required - state.keys())
    if missing:
        return [f"missing top-level fields: {', '.join(missing)}"]
    if state.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if not isinstance(state.get("revision"), int) or state["revision"] < 0:
        errors.append("revision must be a non-negative integer")
    _validate_timestamp(state.get("created_at"), "created_at", errors)
    _validate_timestamp(state.get("updated_at"), "updated_at", errors)
    _validate_project(state.get("project"), errors)
    if not isinstance(state.get("glossary"), dict) or any(
        not _nonempty(str(key)) or not _nonempty(value)
        for key, value in (state.get("glossary") or {}).items()
    ):
        errors.append("glossary must map non-empty terms to non-empty definitions")
    if state.get("current_stage") not in STAGES:
        errors.append(f"current_stage must be one of: {', '.join(STAGES)}")

    records: dict[str, dict[str, dict[str, Any]]] = {}
    for name, prefix in COLLECTION_PREFIXES.items():
        records[name] = _validate_collection(state.get(name), name, prefix, errors)

    _validate_approvals(state.get("approvals"), errors)
    _validate_string_list(state.get("stop_conditions"), "stop_conditions", errors)
    _validate_evidence(records["evidence"], errors)
    _validate_routes(records["routes"], errors)
    _validate_working_propositions(records["working_propositions"], errors)
    _validate_protocols(records["protocols"], errors)
    _validate_observations(records["observations"], errors)
    _validate_artifacts(records["artifacts"], errors)
    _validate_claims(records["claims"], errors)
    _validate_conflicts(records["conflicts"], errors)
    _validate_tasks(records["tasks"], state, errors)
    _validate_references(records, errors)
    _validate_task_graph(records["tasks"], errors)
    _validate_gates(state, records, errors)
    if previous is not None:
        _validate_update_invariants(previous, state, errors)
    return errors


def validate_or_raise(state: Any, *, previous: dict[str, Any] | None = None) -> None:
    errors = validation_errors(state, previous=previous)
    if errors:
        raise ValueError("\n".join(f"- {error}" for error in errors))


def validate_workspace(workspace: Path) -> list[str]:
    state_path = workspace / "research_state.json"
    if not state_path.is_file():
        return [f"missing {state_path}"]
    try:
        state = load_state(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    errors = validation_errors(state)
    for directory in (".checkpoints", "artifacts", "orchestration/tasks", "orchestration/reports"):
        if not (workspace / directory).is_dir():
            errors.append(f"missing workspace directory: {directory}")
    for artifact in state.get("artifacts", []):
        if artifact.get("status") != "available" or not _safe_relative_path(artifact.get("path")):
            continue
        artifact_path = (workspace / artifact["path"]).resolve()
        if not artifact_path.is_relative_to(workspace.resolve()):
            errors.append(f"{artifact.get('id')}.path resolves outside the workspace")
        elif not artifact_path.is_file():
            errors.append(f"{artifact.get('id')}.path does not exist")
        elif hashlib.sha256(artifact_path.read_bytes()).hexdigest() != artifact.get("sha256"):
            errors.append(f"{artifact.get('id')}.sha256 does not match the file")
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
    extra_files: Iterable[tuple[Path, bytes]] = (),
) -> dict[str, Any]:
    workspace = workspace.resolve()
    if actor.strip() != CANONICAL_WRITER:
        raise ValueError(f"canonical state may only be written by {CANONICAL_WRITER!r}")
    state_path = workspace / "research_state.json"
    current = load_state(state_path)
    candidate = deepcopy(candidate)
    if candidate.get("revision") != current.get("revision"):
        raise ValueError("candidate revision is stale; reload research_state.json")
    if candidate.get("created_at") != current.get("created_at"):
        raise ValueError("created_at is immutable")
    if candidate.get("project", {}).get("id") != current.get("project", {}).get("id"):
        raise ValueError("project.id is immutable")
    validate_or_raise(candidate, previous=current)

    evidence_path = workspace / "evidence.jsonl"
    decisions_path = workspace / "decisions.jsonl"
    logged_evidence = load_jsonl(evidence_path)
    if logged_evidence != current["evidence"]:
        raise ValueError("evidence log drift detected; validate the workspace first")
    logged_decisions = load_jsonl(decisions_path)
    if logged_decisions and logged_decisions[-1].get("revision") != current["revision"]:
        raise ValueError("decision log drift detected; validate the workspace first")
    if not logged_decisions and current["revision"] != 0:
        raise ValueError("decision log drift detected; validate the workspace first")
    action, rationale = action.strip(), rationale.strip()
    if not action or not rationale:
        raise ValueError("action and rationale must not be empty")
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
    new_evidence = candidate["evidence"][len(current["evidence"]):]
    decision = {
        "timestamp": candidate["updated_at"],
        "revision": next_revision,
        "actor": CANONICAL_WRITER,
        "action": action,
        "rationale": rationale,
        "stage_from": current["current_stage"],
        "stage_to": candidate["current_stage"],
        "evidence_ids": list(evidence_ids),
    }
    additional: list[tuple[Path, bytes]] = []
    reserved = {checkpoint, evidence_path, decisions_path, state_path, workspace / "research_summary.md"}
    for path, content in extra_files:
        path = path.resolve()
        if not path.is_relative_to(workspace):
            raise ValueError(f"transaction file escapes workspace: {path}")
        if path in reserved:
            raise ValueError(f"transaction file collides with canonical path: {path}")
        if not isinstance(content, bytes):
            raise ValueError("transaction file content must be bytes")
        reserved.add(path)
        additional.append((path, content))
    atomic_replace_bundle((
        (checkpoint, _json_bytes(current)),
        (evidence_path, _jsonl_bytes([*logged_evidence, *new_evidence])),
        (decisions_path, _jsonl_bytes([*logged_decisions, decision])),
        (state_path, _json_bytes(candidate)),
        (workspace / "research_summary.md", render_summary(candidate).encode("utf-8")),
        *additional,
    ))
    return decision


def render_summary(state: dict[str, Any]) -> str:
    approvals = state["approvals"]
    lines = [
        f"# Research Summary: {state['project']['id']}", "",
        f"- Schema: `{state['schema_version']}`",
        f"- Revision: {state['revision']}",
        f"- Stage: `{state['current_stage']}`",
        f"- Updated: {state['updated_at']}", "",
        "## Research question", "", state["project"]["question"], "",
        "## Scope", "", *_render_bullets(state["project"]["scope"]), "",
        "## Gates", "", "| Gate | Status | Approved by |", "|---|---|---|",
    ]
    for name in APPROVAL_NAMES:
        approval = approvals[name]
        lines.append(f"| {name} | {approval['status']} | {approval.get('by') or '-'} |")

    task_groups = {
        "ready": [task for task in state["tasks"] if task.get("status") == "ready"],
        "assigned": [task for task in state["tasks"] if task.get("status") == "assigned"],
        "running": [task for task in state["tasks"] if task.get("status") == "running"],
        "waiting-human": [task for task in state["tasks"] if task.get("status") == "waiting_human"],
        "batch-review": [task for task in state["tasks"] if task.get("human_level") == "H1" and task.get("status") == "merged"],
        "stale-report": [task for task in state["tasks"] if task.get("status") == "needs_rework"],
        "blocked": [task for task in state["tasks"] if task.get("status") == "blocked"],
    }
    lines.extend(("", "## Task queues", "", "| Queue | Count | Task IDs |", "|---|---:|---|"))
    for status, tasks in task_groups.items():
        ids = ", ".join(f"`{task['id']}`" for task in tasks) or "-"
        lines.append(f"| {status} | {len(tasks)} | {ids} |")
    conflict_ids = ", ".join(f"`{item['id']}`" for item in state["conflicts"] if item.get("status") == "open") or "-"
    open_conflicts = sum(item.get("status") == "open" for item in state["conflicts"])
    lines.append(f"| conflict | {open_conflicts} | {conflict_ids} |")

    sections = (
        ("Open uncertainties", state["uncertainties"], "question"),
        ("Evidence", state["evidence"], "proposition"),
        ("Research routes", state["routes"], "method_family"),
        ("Working propositions", state["working_propositions"], "statement"),
        ("Protocols", state["protocols"], "title"),
        ("Observations", state["observations"], "description"),
        ("Claims", state["claims"], "statement"),
        ("Conflicts", state["conflicts"], "statement"),
        ("Evidence gaps", state["open_evidence_gaps"], "question"),
    )
    for title, records, text_key in sections:
        lines.extend(("", f"## {title}", ""))
        if not records:
            lines.append("- None recorded.")
            continue
        for record in records:
            suffix = f" [{record['status']}]" if record.get("status") else ""
            lines.append(f"- `{record['id']}`{suffix}: {record.get(text_key, '')}")
    lines.append("")
    return "\n".join(lines)


def write_summary(workspace: Path, state: dict[str, Any]) -> None:
    path = workspace / "research_summary.md"
    content = render_summary(state)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
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
        if not _nonempty(project.get(field)):
            errors.append(f"project.{field} must be a non-empty string")
    for field in ("scope", "non_goals", "constraints"):
        _validate_string_list(project.get(field), f"project.{field}", errors)
    if not isinstance(project.get("resources"), dict):
        errors.append("project.resources must be an object")


def _validate_string_list(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, list) or any(not _nonempty(item) for item in value):
        errors.append(f"{field} must be a list of non-empty strings")


def _validate_collection(value: Any, name: str, prefix: str, errors: list[str]) -> dict[str, dict[str, Any]]:
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
    if not isinstance(value, dict) or set(value) != set(APPROVAL_NAMES):
        errors.append(f"approvals must contain exactly: {', '.join(APPROVAL_NAMES)}")
        return
    for name in APPROVAL_NAMES:
        approval = value[name]
        if not isinstance(approval, dict):
            errors.append(f"approvals.{name} must be an object")
            continue
        if approval.get("status") not in APPROVAL_STATUSES:
            errors.append(f"approvals.{name}.status is invalid")
        if approval.get("status") == "approved":
            if not _nonempty(approval.get("by")):
                errors.append(f"approvals.{name}.by is required when approved")
            _validate_timestamp(approval.get("at"), f"approvals.{name}.at", errors)
            if name in {"direction", "execution"} and not _nonempty(approval.get("note")):
                errors.append(f"approvals.{name}.note must identify the selected route or action")


def _validate_evidence(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    required = {
        "id", "proposition", "stance", "source_kind", "source_id", "source_lineage",
        "source_depth", "locator", "limitations", "confidence",
    }
    for record_id, record in records.items():
        missing = sorted(required - record.keys())
        if missing:
            errors.append(f"{record_id} missing fields: {', '.join(missing)}")
            continue
        for field in ("proposition", "source_id", "source_lineage"):
            if not _nonempty(record.get(field)):
                errors.append(f"{record_id}.{field} must be a non-empty string")
        if record.get("stance") not in EVIDENCE_STANCES:
            errors.append(f"{record_id}.stance is invalid")
        if record.get("source_kind") not in SOURCE_KINDS:
            errors.append(f"{record_id}.source_kind is invalid")
        if record.get("source_depth") not in SOURCE_DEPTHS:
            errors.append(f"{record_id}.source_depth is invalid")
        if not isinstance(record.get("locator"), dict):
            errors.append(f"{record_id}.locator must be an object")
        if record.get("source_depth") in {"full_text", "artifact", "direct_observation", "dataset", "expert_attestation"} and not record.get("locator"):
            errors.append(f"{record_id}.locator is required for inspected evidence")
        if record.get("source_depth") == "metadata" and record.get("stance") not in {"context", "inconclusive"}:
            errors.append(f"{record_id}: metadata cannot support or contradict a claim")
        _validate_string_list(record.get("limitations"), f"{record_id}.limitations", errors)
        confidence = record.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
            errors.append(f"{record_id}.confidence must be between 0 and 1")


def _validate_routes(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    required = {
        "id", "epistemic_goal", "method_family", "required_capabilities",
        "executor_mix", "validation_strategy", "uncertainty_ids", "risks", "status",
    }
    for record_id, record in records.items():
        missing = sorted(required - record.keys())
        if missing:
            errors.append(f"{record_id} missing fields: {', '.join(missing)}")
            continue
        if record.get("epistemic_goal") not in EPISTEMIC_GOALS:
            errors.append(f"{record_id}.epistemic_goal is invalid")
        if not _nonempty(record.get("method_family")) or not _nonempty(record.get("validation_strategy")):
            errors.append(f"{record_id} needs method_family and validation_strategy")
        _validate_string_list(record.get("required_capabilities"), f"{record_id}.required_capabilities", errors)
        _validate_string_list(record.get("risks"), f"{record_id}.risks", errors)
        if not isinstance(record.get("executor_mix"), list) or any(item not in ROUTE_EXECUTORS for item in record.get("executor_mix", [])):
            errors.append(f"{record_id}.executor_mix contains an invalid executor")
        if record.get("status") not in ROUTE_STATUSES:
            errors.append(f"{record_id}.status is invalid")


def _validate_working_propositions(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    for record_id, record in records.items():
        if record.get("kind") not in PROPOSITION_KINDS:
            errors.append(f"{record_id}.kind is invalid")
        if not _nonempty(record.get("statement")):
            errors.append(f"{record_id}.statement must be non-empty")
        _validate_string_list(record.get("assumptions"), f"{record_id}.assumptions", errors)
        if record.get("status") not in PROPOSITION_STATUSES:
            errors.append(f"{record_id}.status is invalid")


def _validate_protocols(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    for record_id, record in records.items():
        if not _nonempty(record.get("title")) or not _nonempty(record.get("purpose")):
            errors.append(f"{record_id} needs title and purpose")
        for field in ("steps", "inputs", "expected_observations", "stop_conditions", "artifact_paths"):
            _validate_string_list(record.get(field), f"{record_id}.{field}", errors)
        if not _nonempty(record.get("validation")):
            errors.append(f"{record_id}.validation must be non-empty")
        if not isinstance(record.get("budget"), dict):
            errors.append(f"{record_id}.budget must be an object")
        if record.get("status") not in PROTOCOL_STATUSES:
            errors.append(f"{record_id}.status is invalid")


def _validate_observations(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    for record_id, record in records.items():
        if not _nonempty(record.get("description")):
            errors.append(f"{record_id}.description must be non-empty")
        _validate_string_list(record.get("limitations"), f"{record_id}.limitations", errors)
        if record.get("status") not in OBSERVATION_STATUSES:
            errors.append(f"{record_id}.status is invalid")
        if not record.get("task_id") and not record.get("protocol_ids"):
            errors.append(f"{record_id} must reference a task or protocol")


def _validate_artifacts(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    for record_id, record in records.items():
        if not _safe_relative_path(record.get("path")):
            errors.append(f"{record_id}.path must be a safe workspace-relative path")
        if not isinstance(record.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            errors.append(f"{record_id}.sha256 must be lowercase SHA-256")
        for field in ("media_type", "description", "provenance"):
            if not _nonempty(record.get(field)):
                errors.append(f"{record_id}.{field} must be non-empty")
        if record.get("status") not in ARTIFACT_STATUSES:
            errors.append(f"{record_id}.status is invalid")


def _validate_claims(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    for record_id, record in records.items():
        if not _nonempty(record.get("statement")):
            errors.append(f"{record_id}.statement must be non-empty")
        if record.get("status") not in CLAIM_STATUSES:
            errors.append(f"{record_id}.status is invalid")
        _validate_string_list(record.get("caveats"), f"{record_id}.caveats", errors)
        if record.get("status") in {"inference", "supported", "refuted", "needs_review"} and not (
            record.get("evidence_ids") or record.get("observation_ids")
        ):
            errors.append(f"{record_id}: this claim status requires evidence or observations")


def _validate_conflicts(records: dict[str, dict[str, Any]], errors: list[str]) -> None:
    for record_id, record in records.items():
        if not _nonempty(record.get("statement")):
            errors.append(f"{record_id}.statement must be non-empty")
        if record.get("severity") not in CONFLICT_SEVERITIES:
            errors.append(f"{record_id}.severity is invalid")
        if record.get("status") not in CONFLICT_STATUSES:
            errors.append(f"{record_id}.status is invalid")
        if not isinstance(record.get("record_ids"), list) or len(record.get("record_ids", [])) < 2:
            errors.append(f"{record_id}.record_ids must contain at least two ids")


def _validate_tasks(records: dict[str, dict[str, Any]], state: dict[str, Any], errors: list[str]) -> None:
    required = {
        "id", "parent_task_id", "title", "task_kind", "epistemic_role", "question",
        "uncertainty_ids", "human_level", "human_level_override", "executor", "status",
        "depends_on", "priority", "input_snapshot", "execution", "output_contract",
        "validation", "merge", "human_handoff",
    }
    write_scopes: dict[str, str] = {}
    for task_id, task in records.items():
        missing = sorted(required - task.keys())
        if missing:
            errors.append(f"{task_id} missing fields: {', '.join(missing)}")
            continue
        for field in ("title", "epistemic_role", "question"):
            if not _nonempty(task.get(field)):
                errors.append(f"{task_id}.{field} must be non-empty")
        if task.get("task_kind") not in TASK_KINDS:
            errors.append(f"{task_id}.task_kind is invalid")
        if task.get("human_level") not in HUMAN_LEVELS:
            errors.append(f"{task_id}.human_level is invalid")
        if task.get("executor") not in EXECUTORS:
            errors.append(f"{task_id}.executor is invalid")
        if task.get("status") not in TASK_STATUSES:
            errors.append(f"{task_id}.status is invalid")
        if not isinstance(task.get("priority"), int) or not 0 <= task["priority"] <= 100:
            errors.append(f"{task_id}.priority must be an integer from 0 to 100")
        parent = task.get("parent_task_id")
        if parent is not None and not isinstance(parent, str):
            errors.append(f"{task_id}.parent_task_id must be a task id or null")

        snapshot = task.get("input_snapshot")
        if not isinstance(snapshot, dict):
            errors.append(f"{task_id}.input_snapshot must be an object")
        else:
            revision = snapshot.get("research_revision")
            context_hash = snapshot.get("context_hash")
            if revision is not None and (not isinstance(revision, int) or revision < 0 or revision > state.get("revision", -1)):
                errors.append(f"{task_id}.input_snapshot.research_revision is invalid")
            if context_hash is not None and (
                not isinstance(context_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", context_hash)
            ):
                errors.append(f"{task_id}.input_snapshot.context_hash must be SHA-256 or null")
            for field in ("route_ids", "protocol_ids", "evidence_ids", "claim_ids", "artifact_ids"):
                if not isinstance(snapshot.get(field, []), list) or any(not isinstance(item, str) for item in snapshot.get(field, [])):
                    errors.append(f"{task_id}.input_snapshot.{field} must be a list of ids")
            if task.get("status") in {"ready", "assigned", "running", "reported", "validating", "merged"} and (
                revision is None or context_hash is None
            ):
                errors.append(f"{task_id}: active tasks require a frozen input snapshot")

        execution = task.get("execution")
        if not isinstance(execution, dict):
            errors.append(f"{task_id}.execution must be an object")
        else:
            if execution.get("mode") not in EXECUTION_MODES:
                errors.append(f"{task_id}.execution.mode is invalid")
            read_scope = execution.get("read_scope")
            if not isinstance(read_scope, list) or any(not _safe_relative_path(item) for item in read_scope):
                errors.append(f"{task_id}.execution.read_scope must contain safe workspace-relative paths")
            else:
                canonical_paths = {"research_state.json", "evidence.jsonl", "decisions.jsonl"}
                forbidden = sorted(set(read_scope) & canonical_paths)
                if forbidden:
                    errors.append(f"{task_id}.execution.read_scope cannot expose canonical state files")
                artifact_index = {item.get("id"): item for item in state.get("artifacts", [])}
                required_paths = {
                    artifact_index[item_id]["path"]
                    for item_id in task.get("input_snapshot", {}).get("artifact_ids", [])
                    if item_id in artifact_index
                }
                missing_paths = sorted(required_paths - set(read_scope))
                if missing_paths:
                    errors.append(f"{task_id}.execution.read_scope omits input artifacts: {', '.join(missing_paths)}")
            scope = execution.get("write_scope")
            expected_scope = f"orchestration/tasks/{task_id}"
            if scope != expected_scope:
                errors.append(f"{task_id}.execution.write_scope must be {expected_scope!r}")
            elif scope in write_scopes:
                errors.append(f"tasks {write_scopes[scope]} and {task_id} share a write_scope")
            else:
                write_scopes[scope] = task_id
            _validate_string_list(execution.get("resource_locks"), f"{task_id}.execution.resource_locks", errors)
            _validate_string_list(execution.get("side_effects"), f"{task_id}.execution.side_effects", errors)
            if execution.get("parallel_group") is not None and not _nonempty(execution.get("parallel_group")):
                errors.append(f"{task_id}.execution.parallel_group must be non-empty or null")

        output_contract = task.get("output_contract")
        if not isinstance(output_contract, dict):
            errors.append(f"{task_id}.output_contract must be an object")
        else:
            _validate_string_list(output_contract.get("artifact_types"), f"{task_id}.output_contract.artifact_types", errors)
            for field in ("may_propose_evidence", "may_propose_claims"):
                if not isinstance(output_contract.get(field), bool):
                    errors.append(f"{task_id}.output_contract.{field} must be boolean")

        validation = task.get("validation")
        if not isinstance(validation, dict):
            errors.append(f"{task_id}.validation must be an object")
        else:
            if validation.get("mode") not in VALIDATION_MODES:
                errors.append(f"{task_id}.validation.mode is invalid")
            if not isinstance(validation.get("requires_human"), bool):
                errors.append(f"{task_id}.validation.requires_human must be boolean")
            _validate_string_list(validation.get("acceptance_criteria"), f"{task_id}.validation.acceptance_criteria", errors)

        merge = task.get("merge")
        if not isinstance(merge, dict):
            errors.append(f"{task_id}.merge must be an object")
        else:
            if merge.get("strategy") not in MERGE_STRATEGIES:
                errors.append(f"{task_id}.merge.strategy is invalid")
            if merge.get("conflict_policy") != "preserve_and_escalate":
                errors.append(f"{task_id}.merge.conflict_policy must be preserve_and_escalate")
            if merge.get("required_gate") not in GATE_NAMES:
                errors.append(f"{task_id}.merge.required_gate is invalid")

        if task.get("human_level") in {"H3", "H4"}:
            _validate_handoff(task_id, task.get("human_handoff"), errors)
        elif task.get("human_handoff") is not None:
            errors.append(f"{task_id}.human_handoff must be null below H3")
        if task.get("human_level") == "H4" and task.get("executor") in {"main_agent", "subagent"}:
            errors.append(f"{task_id}: H4 tasks cannot be executed by an agent")


def _validate_handoff(task_id: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{task_id}.human_handoff is required for H3/H4")
        return
    if not _nonempty(value.get("action")) or not _nonempty(value.get("resume_condition")):
        errors.append(f"{task_id}.human_handoff needs action and resume_condition")
    for field in (
        "prerequisites", "quality_requirements", "expected_artifacts",
        "bias_fields", "deviation_fields",
    ):
        _validate_string_list(value.get(field), f"{task_id}.human_handoff.{field}", errors)


def _validate_references(records: dict[str, dict[str, dict[str, Any]]], errors: list[str]) -> None:
    evidence_ids = set(records["evidence"])
    observation_ids = set(records["observations"])
    route_ids = set(records["routes"])
    task_ids = set(records["tasks"])
    artifact_ids = set(records["artifacts"])
    protocol_ids = set(records["protocols"])
    uncertainty_ids = set(records["uncertainties"])
    all_ids = set().union(*(set(collection) for collection in records.values()))
    for record_id, record in records["claims"].items():
        _check_refs(record, "evidence_ids", evidence_ids, record_id, errors)
        _check_refs(record, "observation_ids", observation_ids, record_id, errors)
    for record_id, record in records["working_propositions"].items():
        _check_refs(record, "evidence_ids", evidence_ids, record_id, errors)
    for record_id, record in records["routes"].items():
        _check_refs(record, "uncertainty_ids", uncertainty_ids, record_id, errors)
    for record_id, record in records["protocols"].items():
        _check_refs(record, "route_ids", route_ids, record_id, errors)
    for record_id, record in records["observations"].items():
        task_id = record.get("task_id")
        if task_id is not None and task_id not in task_ids:
            errors.append(f"{record_id}.task_id references unknown task")
        _check_refs(record, "protocol_ids", protocol_ids, record_id, errors)
        _check_refs(record, "artifact_ids", artifact_ids, record_id, errors)
    for task_id, task in records["tasks"].items():
        if task.get("parent_task_id") is not None and task["parent_task_id"] not in task_ids:
            errors.append(f"{task_id}.parent_task_id references unknown task")
        _check_refs(task, "uncertainty_ids", uncertainty_ids, task_id, errors)
        _check_refs(task, "depends_on", task_ids, task_id, errors)
        snapshot = task.get("input_snapshot", {})
        _check_refs(snapshot, "route_ids", route_ids, task_id, errors)
        _check_refs(snapshot, "protocol_ids", protocol_ids, task_id, errors)
        _check_refs(snapshot, "evidence_ids", evidence_ids, task_id, errors)
        _check_refs(snapshot, "claim_ids", set(records["claims"]), task_id, errors)
        _check_refs(snapshot, "artifact_ids", artifact_ids, task_id, errors)
    for record_id, record in records["conflicts"].items():
        _check_refs(record, "record_ids", all_ids, record_id, errors)


def _check_refs(record: dict[str, Any], field: str, known: set[str], record_id: str, errors: list[str]) -> None:
    value = record.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{record_id}.{field} must be a list of ids")
        return
    unknown = sorted(set(value) - known)
    if unknown:
        errors.append(f"{record_id}.{field} references unknown ids: {', '.join(unknown)}")


def _validate_task_graph(tasks: dict[str, dict[str, Any]], errors: list[str]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, path: list[str]) -> None:
        if task_id in visiting:
            start = path.index(task_id)
            errors.append("task dependency cycle: " + " -> ".join(path[start:] + [task_id]))
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        path.append(task_id)
        for dependency in tasks.get(task_id, {}).get("depends_on", []):
            if dependency in tasks:
                visit(dependency, path)
        path.pop()
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(tasks):
        visit(task_id, [])
    for task_id, task in tasks.items():
        if task_id in task.get("depends_on", []):
            errors.append(f"{task_id} cannot depend on itself")
        if task.get("status") in {"ready", "assigned", "running", "reported", "validating", "merged"}:
            incomplete = [dep for dep in task.get("depends_on", []) if tasks.get(dep, {}).get("status") != "merged"]
            if incomplete:
                errors.append(f"{task_id} has incomplete dependencies: {', '.join(incomplete)}")


def _validate_gates(state: dict[str, Any], records: dict[str, dict[str, dict[str, Any]]], errors: list[str]) -> None:
    stage = state.get("current_stage")
    approvals = state.get("approvals", {})
    if stage != "framing":
        if approvals.get("scope", {}).get("status") != "approved":
            errors.append("Scope Gate: approve scope before leaving framing")
        if not state.get("project", {}).get("scope"):
            errors.append("Scope Gate: project.scope must not be empty")
    if stage in {"planning", "working"}:
        if approvals.get("direction", {}).get("status") != "approved":
            errors.append("Direction Gate: approve selected routes before planning or working")
        if not any(route.get("status") in {"selected", "active", "completed"} for route in records["routes"].values()):
            errors.append("Direction Gate: at least one route must be selected")
    for task_id, task in records["tasks"].items():
        if task.get("status") not in {"ready", "assigned", "running", "reported", "validating", "merged"}:
            continue
        gate = task.get("merge", {}).get("required_gate")
        if gate and approvals.get(gate, {}).get("status") != "approved":
            errors.append(f"{task_id}: required {gate} gate is not approved")
        if task.get("execution", {}).get("mode") == "execute_external" and approvals.get("execution", {}).get("status") != "approved":
            errors.append(f"{task_id}: external execution requires Execution Gate")
    if stage == "complete":
        if approvals.get("claim", {}).get("status") != "approved":
            errors.append("Claim Gate: human approval is required before completion")
        if not records["claims"]:
            errors.append("Claim Gate: record at least one bounded claim")


def _validate_update_invariants(previous: dict[str, Any], candidate: dict[str, Any], errors: list[str]) -> None:
    old_stage, new_stage = previous.get("current_stage"), candidate.get("current_stage")
    if old_stage in ALLOWED_TRANSITIONS and new_stage not in ALLOWED_TRANSITIONS[old_stage]:
        errors.append(f"invalid stage transition: {old_stage} -> {new_stage}")
    old_evidence, new_evidence = previous.get("evidence", []), candidate.get("evidence", [])
    if not isinstance(new_evidence, list) or new_evidence[:len(old_evidence)] != old_evidence:
        errors.append("evidence is append-only; existing packets cannot change or disappear")
    boundary_fields = ("question", "scope", "non_goals", "constraints")
    if any(previous.get("project", {}).get(field) != candidate.get("project", {}).get(field) for field in boundary_fields):
        if new_stage != "framing":
            errors.append("material scope changes must return the project to framing")
        for gate in ("direction", "plan", "execution", "claim"):
            if candidate.get("approvals", {}).get(gate, {}).get("status") == "approved":
                errors.append(f"material scope changes must reset the {gate} approval")
    previous_selected = {item["id"] for item in previous.get("routes", []) if item.get("status") in {"selected", "active"}}
    candidate_selected = {item["id"] for item in candidate.get("routes", []) if item.get("status") in {"selected", "active"}}
    if previous_selected != candidate_selected:
        old_direction = previous.get("approvals", {}).get("direction", {}).get("status")
        new_direction = candidate.get("approvals", {}).get("direction", {}).get("status")
        if old_direction == "approved" and new_direction == "approved":
            errors.append("selected route changes must reset Direction Gate")
    if previous.get("protocols") != candidate.get("protocols"):
        for gate in ("plan", "execution"):
            if candidate.get("approvals", {}).get(gate, {}).get("status") == "approved":
                errors.append(f"protocol changes must reset the {gate} approval")
    previous_tasks = {item["id"]: item for item in previous.get("tasks", [])}
    for task in candidate.get("tasks", []):
        old = previous_tasks.get(task.get("id"))
        if old is None:
            continue
        old_status, new_status = old.get("status"), task.get("status")
        if old_status in TASK_TRANSITIONS and new_status not in TASK_TRANSITIONS[old_status]:
            errors.append(f"invalid task transition for {task['id']}: {old_status} -> {new_status}")
        old_level, new_level = old.get("human_level"), task.get("human_level")
        if old_level in HUMAN_LEVELS and new_level in HUMAN_LEVELS and HUMAN_LEVELS.index(new_level) < HUMAN_LEVELS.index(old_level):
            override = task.get("human_level_override")
            if not isinstance(override, dict) or not all(_nonempty(override.get(field)) for field in ("approved_by", "at", "reason")):
                errors.append(f"{task['id']}: lowering human_level requires a human override")
            else:
                _validate_timestamp(override.get("at"), f"{task['id']}.human_level_override.at", errors)


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _render_bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] or ["- Not yet approved."]
