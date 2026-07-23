"""Run anonymous paper discovery and emit a JSON manifest."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = PLUGIN_ROOT / "runtime" / "python"
sys.path.insert(0, str(RUNTIME_ROOT))

from researching_skill_runtime import (  # noqa: E402
    PaperRecord,
    build_login_notice,
    create_discovery_service,
)
from researching_skill_runtime.certification import (  # noqa: E402
    create_credential_store,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.resolve_oa and not args.email:
        parser.error("--resolve-oa requires --email")
    openalex_api_key = _load_optional_api_key(args.openalex_account)
    service = create_discovery_service(
        crossref_mailto=args.email,
        openalex_api_key=openalex_api_key,
        unpaywall_email=args.email if args.resolve_oa else None,
    )
    result = service.discover(args.query, limit_per_provider=args.limit)
    notice = build_login_notice(result.queue, institution=args.institution)
    payload = {
        "query": args.query,
        "manifest": result.manifest.as_dict(),
        "papers": [_paper_payload(paper) for paper in result.queue.papers],
        "login_notice": (
            {"count": notice.count, "message": notice.message}
            if notice
            else None
        ),
        "issues": [asdict(issue) for issue in result.issues],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover paper metadata before institutional login.",
    )
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--email",
        help="Contact email for Crossref polite access and Unpaywall.",
    )
    parser.add_argument(
        "--resolve-oa",
        action="store_true",
        help="Resolve legal OA locations through Unpaywall; requires --email.",
    )
    parser.add_argument(
        "--openalex-account",
        help="OS credential-store account containing an OpenAlex API key.",
    )
    parser.add_argument(
        "--institution",
        help="Institution label used only in the login notice.",
    )
    return parser


def _load_optional_api_key(account: str | None) -> str | None:
    if account is None:
        return None
    return create_credential_store(
        service_name="researching-plugin.api-keys",
    ).require_secret(account)


def _paper_payload(paper: PaperRecord) -> dict[str, object]:
    values = asdict(paper)
    access_status = values.get("access_status")
    if access_status is not None:
        values["access_status"] = str(access_status)
    return values


if __name__ == "__main__":
    raise SystemExit(main())
