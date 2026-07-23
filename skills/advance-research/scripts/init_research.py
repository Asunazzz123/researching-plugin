#!/usr/bin/env python3
"""Initialize a durable local research workspace."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state import create_workspace, initial_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--question", required=True)
    parser.add_argument("--project-id")
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--non-goal", action="append", default=[])
    parser.add_argument("--constraint", action="append", default=[])
    parser.add_argument(
        "--resources-json",
        default="{}",
        help="JSON object describing available compute, data, time, or tools",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    resources = json.loads(args.resources_json)
    if not isinstance(resources, dict):
        raise SystemExit("--resources-json must decode to an object")
    state = initial_state(
        args.question,
        project_id=args.project_id,
        scope=args.scope,
        non_goals=args.non_goal,
        constraints=args.constraint,
        resources=resources,
    )
    create_workspace(args.workspace.resolve(), state)
    print(args.workspace.resolve() / "research_state.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
