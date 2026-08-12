#!/usr/bin/env python3
"""Regenerate the human-readable research summary from canonical state."""

from __future__ import annotations

import argparse
from pathlib import Path

from research_state import load_state, validate_or_raise, write_summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    state = load_state(workspace / "research_state.json")
    validate_or_raise(state)
    write_summary(workspace, state)
    print(workspace / "research_summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
