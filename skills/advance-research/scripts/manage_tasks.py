#!/usr/bin/env python3
"""Manage schema-v2 task contexts, frontiers, reports, reducers, and handoffs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state import CANONICAL_WRITER, load_json, load_state
from task_orchestration import (
    build_context_packet,
    merge_report,
    prepare_task_context,
    ready_frontier,
    render_handoff,
    start_tasks,
    validate_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    frontier = subparsers.add_parser("frontier", help="Select a deterministic ready batch.")
    frontier.add_argument("workspace", type=Path)
    frontier.add_argument("--max-parallel", type=int, default=3)

    context = subparsers.add_parser("context", help="Build or prepare a frozen Context Packet.")
    context.add_argument("workspace", type=Path)
    context.add_argument("task_id")
    context.add_argument(
        "--prepare",
        action="store_true",
        help="Commit the snapshot and write context.json through the main-agent writer.",
    )

    start = subparsers.add_parser("start", help="Mark a selected frontier batch running.")
    start.add_argument("workspace", type=Path)
    start.add_argument("task_id", nargs="+")

    validate = subparsers.add_parser("validate-report", help="Validate a task-local report.")
    validate.add_argument("workspace", type=Path)
    validate.add_argument("report", type=Path)

    merge = subparsers.add_parser("merge-report", help="Merge a validated H0/H1 report.")
    merge.add_argument("workspace", type=Path)
    merge.add_argument("report", type=Path)

    handoff = subparsers.add_parser("handoff", help="Render an H3/H4 Human Handoff.")
    handoff.add_argument("workspace", type=Path)
    handoff.add_argument("task_id")
    handoff.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = args.workspace.resolve()
    if args.command == "frontier":
        result = ready_frontier(
            load_state(workspace / "research_state.json"),
            max_parallel=args.max_parallel,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "context":
        result = (
            prepare_task_context(workspace, args.task_id)
            if args.prepare
            else build_context_packet(
                load_state(workspace / "research_state.json"), args.task_id
            )
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate-report":
        errors = validate_report(workspace, load_json(args.report.resolve()))
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("OK")
        return 0
    if args.command == "start":
        result = start_tasks(workspace, args.task_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "merge-report":
        result = merge_report(
            workspace,
            load_json(args.report.resolve()),
            actor=CANONICAL_WRITER,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "handoff":
        content = render_handoff(
            load_state(workspace / "research_state.json"), args.task_id
        )
        if args.output:
            output = args.output.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
            print(output)
        else:
            print(content, end="")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
