"""学习报告面板：分析近期思维模式。"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QComboBox, QFrame,
)

import core.database as db
from core.ai_client import generate_weekly_report


class ReportWorker(QThread):
    done = Signal(str)
    error = Signal(str)

    def __init__(self, all_text: str):
        super().__init__()
        self.all_text = all_text

    def run(self):
        try:
            result = generate_weekly_report(self.all_text)
            self.done.emit(result)
        except RuntimeError as e:
            self.error.emit(str(e))


class ReportPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ReportWorker | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("学习报告")
        title.setStyleSheet("font-size:18px; font-weight:bold; color:#e6edf3;")
        layout.addWidget(title)

        # 控制栏
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("分析范围："))

        self.range_box = QComboBox()
        self.range_box.addItem("最近 7 天", 7)
        self.range_box.addItem("最近 30 天", 30)
        self.range_box.addItem("全部记录", 0)
        self.range_box.setFixedWidth(130)
        ctrl.addWidget(self.range_box)
        ctrl.addStretch()

        self.gen_btn = QPushButton("生成报告")
        self.gen_btn.setObjectName("primaryBtn")
        self.gen_btn.clicked.connect(self._generate)
        ctrl.addWidget(self.gen_btn)

        self.save_btn = QPushButton("保存到记忆库")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        ctrl.addWidget(self.save_btn)

        layout.addLayout(ctrl)

        self.status_lbl = QLabel("选择范围后点击「生成报告」")
        self.status_lbl.setObjectName("sectionLabel")
        layout.addWidget(self.status_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#21262d; border:none; max-height:1px;")
        layout.addWidget(sep)

        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setStyleSheet("background:#161b22; border:1px solid #30363d; border-radius:6px;")
        layout.addWidget(self.result_edit, 1)

        self._report_text = ""

    def _generate(self):
        if self._worker:
            return

        days = self.range_box.currentData()
        topics = db.get_topics()
        parts = []

        for t in topics:
            msgs = db.get_messages(t["id"])
            if not msgs:
                continue

            if days > 0:
                cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                msgs = [m for m in msgs if m["created_at"][:10] >= cutoff]

            if not msgs:
                continue

            block = f"## {t['name']}\n"
            for m in msgs:
                role = "我" if m["role"] == "user" else "AI"
                block += f"{role}：{m['content'][:200]}\n"
            parts.append(block)

        if not parts:
            self.status_lbl.setText("所选时间范围内没有记录")
            return

        all_text = "\n\n".join(parts)
        self.gen_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.status_lbl.setText("AI 分析中，请稍候…")
        self.result_edit.clear()

        self._worker = ReportWorker(all_text)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, text: str):
        self._worker = None
        self._report_text = text
        self.result_edit.setMarkdown(text)
        self.gen_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_lbl.setText(f"报告生成完成  ·  {datetime.now().strftime('%H:%M')}")

    def _on_error(self, msg: str):
        self._worker = None
        self.gen_btn.setEnabled(True)
        self.status_lbl.setText(f"生成失败：{msg}")

    def _save(self):
        if not self._report_text:
            return
        db.add_insight(self._report_text, insight_type="weekly_report")
        try:
            from core.memory import add_memory
            add_memory(
                doc_id=f"report_{datetime.now().timestamp():.0f}",
                text=self._report_text,
                metadata={
                    "topic_id": "0",
                    "topic_name": "学习报告",
                    "role": "report",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                },
            )
        except Exception:
            pass
        self.save_btn.setEnabled(False)
        self.status_lbl.setText("已保存到记忆库 ✓")
