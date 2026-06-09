from __future__ import annotations

from pathlib import Path

from app.research import service


def test_tdx_report_row_becomes_research_item() -> None:
    row = {
        "title": "半导体行业深度报告：先进封装景气度持续提升",
        "summary": "AI 算力拉动先进封装需求，产业链订单能见度提升。",
        "content": "先进封装产业链包括设备、材料和封测环节。\n重点关注 688012 和 300604。",
        "source_url": "https://data.tdx.com.cn/tdxfiles/yb/sample.pdf",
        "institution": "通达信研报",
        "published_at": "2026-06-08",
        "report_type": "产业报告",
    }
    source = {"name": "通达信问达研报", "source_type": "通达信MCP"}

    item = service._tdx_report_to_item(row, source)

    assert item is not None
    assert item.title.startswith("半导体行业深度报告")
    assert item.report_type == "产业报告"
    assert item.source_name == "通达信问达研报"
    assert item.source_type == "通达信MCP"
    assert item.institution == "通达信研报"
    assert item.industry == "半导体"
    assert item.symbols == ["300604", "688012"]
    assert "已解析全文" in item.tags
    assert item.content.startswith("先进封装产业链")
    assert item.content_hash


def test_local_text_file_import_extracts_title_and_symbols(tmp_path: Path) -> None:
    path = tmp_path / "buyer-model.md"
    path.write_text("# 宁德时代财务模型拆解\n关注 300750 和 688599 的产业链映射。", encoding="utf-8")
    source = {"name": "本地授权文件", "source_type": "用户授权文件", "url": str(tmp_path)}

    items = service._fetch_local_files(source)

    assert len(items) == 1
    assert items[0].title == "宁德时代财务模型拆解"
    assert items[0].report_type == "授权导入"
    assert items[0].symbols == ["300750", "688599"]


def test_configured_sources_adds_authorized_import_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("INDUSTRY_RESEARCH_IMPORT_DIR", str(tmp_path))

    sources = service._configured_sources()

    assert any(source["name"] == "通达信问达研报" and source["kind"] == "tdx_research" for source in sources)
    assert any(source["name"] == "本地授权文件" and source["source_type"] == "用户授权文件" for source in sources)
