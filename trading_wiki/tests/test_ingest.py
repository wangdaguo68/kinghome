import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ingest.py"


def load_ingest_module():
    spec = importlib.util.spec_from_file_location("ingest", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["ingest"] = module
    spec.loader.exec_module(module)
    return module


class IngestWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(REPO_ROOT / "templates", self.root / "templates")
        (self.root / "raw").mkdir()
        self.raw_file = self.root / "raw" / "2026-06-11.md"
        self.raw_file.write_text(
            "\n".join(
                [
                    "# 2026-06-11",
                    "## 概念",
                    "- AI PCB钴针三重通胀：AI服务器PCB高层数带来钻针耗材变化",
                    "- MLCC设备国产替代：高容MLCC扩产带动设备验证",
                    "## 标的",
                    "- 中船特气：WF6纯度、客户、产能需要验证",
                    "## 错误",
                    "- 把群聊传闻直接当成事实",
                ]
            ),
            encoding="utf-8",
        )
        self.ingest = load_ingest_module()

    def tearDown(self):
        self.tmp.cleanup()

    def test_ingest_creates_audit_files_and_knowledge_pages(self):
        code = self.ingest.main(
            [
                "--root",
                str(self.root),
                "--date",
                "2026-06-11",
                "--input",
                "raw/2026-06-11.md",
                "--source-type",
                "group_chat",
            ]
        )

        self.assertEqual(code, 0)
        self.assertTrue((self.root / "sources" / "2026-06-11.md").exists())
        self.assertTrue((self.root / "reviews" / "2026-06-11-wiki-change-review.md").exists())
        self.assertTrue((self.root / "reports" / "2026-06-11-ingest.md").exists())

        concept = self.root / "概念" / "AI PCB钴针三重通胀.md"
        stock = self.root / "股票" / "中船特气.md"
        mistake = self.root / "错误" / "把群聊传闻直接当成事实.md"
        self.assertTrue(concept.exists())
        self.assertTrue(stock.exists())
        self.assertTrue(mistake.exists())
        self.assertIn("source_links:", concept.read_text(encoding="utf-8"))
        self.assertIn("## 验证清单", stock.read_text(encoding="utf-8"))

    def test_second_ingest_appends_update_instead_of_overwriting(self):
        args = [
            "--root",
            str(self.root),
            "--date",
            "2026-06-11",
            "--input",
            "raw/2026-06-11.md",
            "--source-type",
            "group_chat",
        ]
        self.assertEqual(self.ingest.main(args), 0)
        concept = self.root / "概念" / "AI PCB钴针三重通胀.md"
        first_text = concept.read_text(encoding="utf-8")

        self.raw_file.write_text(self.raw_file.read_text(encoding="utf-8") + "\n补充：钻针需要验证ASP和订单。\n", encoding="utf-8")
        self.assertEqual(self.ingest.main(args), 0)
        second_text = concept.read_text(encoding="utf-8")

        self.assertIn("# AI PCB钴针三重通胀", second_text)
        self.assertGreaterEqual(second_text.count("source_hash:"), first_text.count("source_hash:"))

    def test_low_evidence_with_elevated_permission_is_rejected(self):
        bad = self.root / "概念" / "bad.md"
        bad.parent.mkdir(exist_ok=True)
        bad.write_text(
            "\n".join(
                [
                    "---",
                    "type: concept",
                    "evidence_level: low",
                    "execution_permission: candidate",
                    "---",
                    "# bad",
                    "source_links:",
                    "  - \"[[2026-06-11]]\"",
                ]
            ),
            encoding="utf-8",
        )

        warnings = self.ingest.safety_check_generated_files([bad])

        self.assertTrue(any("elevated permission" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
