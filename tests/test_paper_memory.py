from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

from scripts.prepare_paper import prepare_paper


PLUGIN_ROOT = Path(__file__).parents[1]


class PreparePaperTests(unittest.TestCase):
    def test_prepares_page_mapped_markdown_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "research"
            pdf_path = workspace / "pdf" / "source-file.pdf"
            self._write_blank_pdf(pdf_path, page_count=2, title="Test Paper")

            result = prepare_paper(
                workspace=workspace,
                pdf_path=pdf_path,
                paper_id="arxiv-2502.16982",
            )

            extracted = Path(str(result["extracted_markdown"]))
            record = Path(str(result["record_markdown"]))
            index = Path(str(result["index_markdown"]))
            self.assertEqual(result["page_count"], 2)
            self.assertTrue(result["created_record"])
            self.assertTrue(result["added_to_index"])
            self.assertIn("PDF Page 1", extracted.read_text(encoding="utf-8"))
            self.assertIn("PDF Page 2", extracted.read_text(encoding="utf-8"))
            self.assertIn("# 30-second recall", record.read_text(encoding="utf-8"))
            self.assertIn("../pdf/source-file.pdf", record.read_text(encoding="utf-8"))
            self.assertIn("../pdf/source-file.pdf", index.read_text(encoding="utf-8"))
            self.assertEqual(
                result["warnings"],
                ["pages without extractable text: 1, 2"],
            )

    def test_preserves_existing_durable_record_and_index_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "research"
            pdf_path = workspace / "pdf" / "paper.pdf"
            self._write_blank_pdf(pdf_path)
            first = prepare_paper(
                workspace=workspace,
                pdf_path=pdf_path,
                paper_id="paper-001",
            )
            record = Path(str(first["record_markdown"]))
            record.write_text("researcher notes\n", encoding="utf-8")

            second = prepare_paper(
                workspace=workspace,
                pdf_path=pdf_path,
                paper_id="paper-001",
            )

            self.assertFalse(second["created_record"])
            self.assertFalse(second["added_to_index"])
            self.assertEqual(record.read_text(encoding="utf-8"), "researcher notes\n")

    def test_cli_emits_machine_readable_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "research"
            pdf_path = workspace / "pdf" / "paper.pdf"
            self._write_blank_pdf(pdf_path)

            completed = subprocess.run(
                (
                    sys.executable,
                    str(PLUGIN_ROOT / "scripts" / "prepare_paper.py"),
                    "--workspace",
                    str(workspace),
                    "--pdf",
                    str(pdf_path),
                    "--paper-id",
                    "paper-001",
                ),
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["paper_id"], "paper-001")
            self.assertEqual(payload["page_count"], 1)

    def test_rejects_pdf_outside_workspace_pdf_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "research"
            pdf_path = root / "outside.pdf"
            self._write_blank_pdf(pdf_path)

            with self.assertRaisesRegex(ValueError, "under <workspace>/pdf"):
                prepare_paper(
                    workspace=workspace,
                    pdf_path=pdf_path,
                    paper_id="paper-001",
                )

    def test_rejects_unsafe_paper_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "research"
            pdf_path = workspace / "pdf" / "paper.pdf"
            self._write_blank_pdf(pdf_path)

            with self.assertRaisesRegex(ValueError, "paper-id"):
                prepare_paper(
                    workspace=workspace,
                    pdf_path=pdf_path,
                    paper_id="../paper",
                )

    @staticmethod
    def _write_blank_pdf(
        path: Path, *, page_count: int = 1, title: str | None = None
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        document = pymupdf.open()
        for _ in range(page_count):
            document.new_page(width=200, height=200)
        if title:
            document.set_metadata({"title": title})
        document.save(path)
        document.close()


class PaperMemoryContractTests(unittest.TestCase):
    def test_plugin_distributes_paper_memory_resources(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text()
        )

        self.assertEqual(manifest["version"], "0.7.0")
        self.assertTrue((PLUGIN_ROOT / "references" / "paper-memory.md").is_file())
        self.assertTrue((PLUGIN_ROOT / "scripts" / "prepare_paper.py").is_file())

    def test_skills_define_download_handoff_and_reload_triggers(self) -> None:
        paper_search = (
            PLUGIN_ROOT / "skills" / "researching-paper-searching" / "SKILL.md"
        ).read_text()
        advance = (
            PLUGIN_ROOT / "skills" / "advance-research" / "SKILL.md"
        ).read_text()
        router = (
            PLUGIN_ROOT / "skills" / "using-researching" / "SKILL.md"
        ).read_text()

        self.assertIn("<folder>/pdf/", paper_search)
        self.assertIn("scripts/prepare_paper.py", paper_search)
        self.assertIn("on resume", advance)
        self.assertIn("before stating what literature establishes", advance)
        self.assertIn("not fixed turn counts", advance)
        self.assertIn("papers/index.md", router)


if __name__ == "__main__":
    unittest.main()
