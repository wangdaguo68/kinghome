from __future__ import annotations

from pathlib import Path

from app.research import service


def test_eastmoney_report_row_becomes_research_item() -> None:
    row = {
        "title": "通信行业跟踪报告：CPO规模部署进程有望提速",
        "stockName": "",
        "stockCode": "",
        "orgName": "万联证券股份有限公司",
        "orgSName": "万联证券",
        "publishDate": "2026-06-08 00:00:00.000",
        "infoCode": "AP202606081823367892",
        "industryName": "通信设备",
        "emRatingName": "增持",
        "reportType": 3,
        "researcher": "夏清莹",
        "attachPages": 7,
        "attachSize": 710,
    }
    source = {"name": "东方财富研报中心-行业研报", "source_type": "公开来源", "report_type": "产业报告", "url": "https://data.eastmoney.com/report/industry.jshtml"}

    item = service._eastmoney_row_to_item(row, source)

    assert item is not None
    assert item.title.startswith("通信行业跟踪报告")
    assert item.report_type == "产业报告"
    assert item.source_name == "东方财富研报中心-行业研报"
    assert item.institution == "万联证券"
    assert item.industry == "通信设备"
    assert "7页" in item.tags
    assert "授权渠道导入" in item.summary
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

    assert any(source["name"] == "本地授权文件" and source["source_type"] == "用户授权文件" for source in sources)
