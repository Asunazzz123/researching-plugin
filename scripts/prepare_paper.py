"""Prepare a downloaded PDF as project-local, page-mapped Markdown."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Sequence

import pymupdf


PAPER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = prepare_paper(
        workspace=Path(args.workspace),
        pdf_path=Path(args.pdf),
        paper_id=args.paper_id,
        title=args.title,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create page-mapped Markdown and a durable paper record template.",
    )
    parser.add_argument("--workspace", required=True, help="Research folder root.")
    parser.add_argument("--pdf", required=True, help="PDF under <workspace>/pdf/.")
    parser.add_argument("--paper-id", required=True, help="Filesystem-safe paper ID.")
    parser.add_argument("--title", help="Title override for the Markdown record.")
    return parser


def prepare_paper(
    *,
    workspace: Path,
    pdf_path: Path,
    paper_id: str,
    title: str | None = None,
) -> dict[str, object]:
    """Extract one PDF and initialize its durable project-local record."""

    if not PAPER_ID_PATTERN.fullmatch(paper_id):
        raise ValueError(
            "paper-id must use lowercase letters, digits, dots, underscores, or hyphens"
        )

    workspace = workspace.expanduser().resolve()
    pdf_path = pdf_path.expanduser().resolve(strict=True)
    pdf_root = workspace / "pdf"
    try:
        pdf_path.relative_to(pdf_root)
    except ValueError as exc:
        raise ValueError("PDF must be stored under <workspace>/pdf/") from exc
    if pdf_path.suffix.casefold() != ".pdf":
        raise ValueError("input file must use a .pdf extension")
    if not _has_pdf_signature(pdf_path):
        raise ValueError("input file does not have a PDF signature")

    pages: list[str] = []
    empty_pages: list[int] = []
    extraction_errors: list[str] = []
    with pymupdf.open(pdf_path) as document:
        if document.needs_pass and not document.authenticate(""):
            raise ValueError("PDF is encrypted; provide an authorized decrypted copy")
        if document.page_count == 0:
            raise ValueError("PDF contains no pages")
        resolved_title = _resolve_title(document, title, paper_id)
        page_count = document.page_count
        for page_number, page in enumerate(document, start=1):
            try:
                text = page.get_text("text", sort=True).strip()
            except Exception as exc:  # PyMuPDF raises format-specific exceptions
                text = ""
                extraction_errors.append(
                    f"page {page_number}: {type(exc).__name__}"
                )
            if not text:
                empty_pages.append(page_number)
                text = "[No extractable text; inspect this page visually or run OCR.]"
            pages.append(f"## PDF Page {page_number}\n\n{text}")

    papers_root = workspace / "papers"
    extracted_root = papers_root / ".extracted"
    extracted_root.mkdir(parents=True, exist_ok=True)
    checksum = _sha256(pdf_path)
    extracted_path = extracted_root / f"{paper_id}.md"
    record_path = papers_root / f"{paper_id}.md"
    index_path = papers_root / "index.md"

    extracted_path.write_text(
        _render_extraction(
            paper_id=paper_id,
            title=resolved_title,
            pdf_path=pdf_path,
            checksum=checksum,
            pages=pages,
        ),
        encoding="utf-8",
    )
    created_record = False
    if not record_path.exists():
        record_path.write_text(
            _render_record_template(
                paper_id=paper_id,
                title=resolved_title,
                pdf_path=pdf_path,
                checksum=checksum,
            ),
            encoding="utf-8",
        )
        created_record = True
    added_to_index = _ensure_index_entry(
        index_path=index_path,
        paper_id=paper_id,
        title=resolved_title,
        pdf_name=pdf_path.name,
    )

    warnings: list[str] = []
    if empty_pages:
        warnings.append(
            "pages without extractable text: " + ", ".join(map(str, empty_pages))
        )
    warnings.extend(extraction_errors)
    return {
        "paper_id": paper_id,
        "pdf": str(pdf_path),
        "sha256": checksum,
        "page_count": page_count,
        "extracted_markdown": str(extracted_path),
        "record_markdown": str(record_path),
        "index_markdown": str(index_path),
        "created_record": created_record,
        "added_to_index": added_to_index,
        "warnings": warnings,
    }


def _has_pdf_signature(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(5) == b"%PDF-"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_title(
    document: pymupdf.Document, title: str | None, paper_id: str
) -> str:
    if title and title.strip():
        return title.strip()
    metadata_title = document.metadata.get("title")
    if metadata_title and str(metadata_title).strip():
        return str(metadata_title).strip()
    return paper_id


def _render_extraction(
    *,
    paper_id: str,
    title: str,
    pdf_path: Path,
    checksum: str,
    pages: Sequence[str],
) -> str:
    pdf_link = Path("..", "..", "pdf", pdf_path.name).as_posix()
    return "\n".join(
        (
            "---",
            f"paper_id: {paper_id}",
            f"title: {json.dumps(title, ensure_ascii=False)}",
            f"pdf: {pdf_link}",
            f"sha256: {checksum}",
            f"page_count: {len(pages)}",
            "---",
            "",
            f"# Extracted PDF: {title}",
            "",
            "> Machine-extracted text for navigation. Verify layout-sensitive, visual,",
            "> formula, table, and claim-level details against the original PDF.",
            "",
            *pages,
            "",
        )
    )


def _render_record_template(
    *,
    paper_id: str,
    title: str,
    pdf_path: Path,
    checksum: str,
) -> str:
    pdf_link = Path("..", "pdf", pdf_path.name).as_posix()
    extracted_link = Path(".extracted", f"{paper_id}.md").as_posix()
    return f"""---
paper_id: {paper_id}
title: {json.dumps(title, ensure_ascii=False)}
pdf: {pdf_link}
extracted: {extracted_link}
sha256: {checksum}
status: needs-review
topics: []
---

# 30-second recall

# Current research relevance

# Core contributions

# Method and assumptions

# Main results

| Proposition | Stance | PDF locator | Limitations |
|---|---|---|---|

# Relations to other papers

# Open questions

# Visual checks

| PDF page or figure | What was checked | Result or limitation |
|---|---|---|
"""


def _ensure_index_entry(
    *, index_path: Path, paper_id: str, title: str, pdf_name: str
) -> bool:
    header = (
        "# Paper Index\n\n"
        "Read this file first when resuming the research folder. Load only records "
        "relevant to the active question.\n\n"
        "| Paper ID | Title | Topics | Current relevance | Status | Record | PDF |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    if not index_path.exists():
        index_path.write_text(header, encoding="utf-8")
    content = index_path.read_text(encoding="utf-8")
    if f"| {paper_id} |" in content:
        return False
    safe_title = title.replace("|", "\\|").replace("\n", " ")
    row = (
        f"| {paper_id} | {safe_title} |  |  | needs-review | "
        f"[{paper_id}]({paper_id}.md) | [PDF](../pdf/{pdf_name}) |\n"
    )
    separator = "" if content.endswith("\n") else "\n"
    index_path.write_text(content + separator + row, encoding="utf-8")
    return True


if __name__ == "__main__":
    raise SystemExit(main())
