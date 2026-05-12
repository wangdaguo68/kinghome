"""洞察生成对话框。"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame,
)

import core.database as db
from core.ai_client import generate_insight


class InsightWorker(QThread):
    done = Signal(str)
    error = Signal(str)

    def __init__(self, topic_name: str, history_text: str):
        super().__init__()
        self.topic_name = topic_name
        self.history_text = history_text

    def run(self):
        try:
            result = generate_insight(self.topic_name, self.history_text)
            self.done.emit(result)
        except RuntimeError as e:
            self.error.emit(str(e))


class InsightDialog(QDialog):
    def __init__(self, topic_id: int, topic_name: str, messages: list[dict], parent=None):
        super().__init__(parent)
        self.topic_id = topic_id
        self.topic_name = topic_name
        self.messages = messages
        self.setWindowTitle(f"生成洞察 — {topic_name}")
        self.resize(640, 500)
        self._build_ui()
        self._start()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.status_label = QLabel("AI 正在分析你的思维记录…")
        self.status_label.setStyleSheet("color:#58a6ff; font-size:13px;")
        layout.addWidget(self.status_label)

        self.result_edit = QTextEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setStyleSheet("background:#161b22; border:1px solid #30363d; border-radius:6px;")
        layout.addWidget(self.result_edit, 1)

        btns = QHBoxLayout()
        self.save_btn = QPushButton("保存到记忆库")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        btns.addStretch()
        btns.addWidget(self.save_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _start(self):
        history = "\n\n".join(
            f"{'我' if m['role']=='user' else 'AI'}：{m['content']}"
            for m in self.messages
        )
        self.worker = InsightWorker(self.topic_name, history)
        self.worker.done.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_done(self, text: str):
        self._insight_text = text
        self.result_edit.setMarkdown(text)
        self.status_label.setText("分析完成")
        self.save_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self.status_label.setText(f"错误：{msg}")
        self.result_edit.setPlainText(msg)

    def _save(self):
        db.add_insight(self._insight_text, self.topic_id, "insight")
        try:
            from core.memory import add_memory
            from datetime import datetime
            add_memory(
                doc_id=f"insight_{self.topic_id}_{datetime.now().timestamp():.0f}",
                text=self._insight_text,
                metadata={
                    "topic_id":   str(self.topic_id),
                    "topic_name": self.topic_name,
                    "role":       "insight",
                    "date":       datetime.now().strftime("%Y-%m-%d"),
                },
            )
        except Exception:
            pass
        self.save_btn.setEnabled(False)
        self.status_label.setText("已保存到记忆库 ✓")
