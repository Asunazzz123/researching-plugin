#!/usr/bin/env python3
"""Validate a research workspace and its append-only logs."""

from __future__ import annotations

import argparse
from pathlib import Path

from research_state import validate_workspace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    errors = validate_workspace(args.workspace.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
