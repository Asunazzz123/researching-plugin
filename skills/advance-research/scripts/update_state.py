#!/usr/bin/env python3
"""Commit a validated candidate state with checkpoint and decision logging."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_state import load_json, update_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--action", required=True)
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--evidence-id", action="append", default=[])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    decision = update_workspace(
        args.workspace.resolve(),
        load_json(args.candidate.resolve()),
        action=args.action,
        rationale=args.rationale,
        actor=args.actor,
        evidence_ids=args.evidence_id,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
