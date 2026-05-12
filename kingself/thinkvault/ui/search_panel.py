"""语义搜索面板：全局检索历史记忆。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame,
    QComboBox, QSizePolicy,
)


class SearchWorker(QThread):
    done = Signal(list)
    error = Signal(str)

    def __init__(self, query: str, top_k: int):
        super().__init__()
        self.query = query
        self.top_k = top_k

    def run(self):
        try:
            from core.memory import search_memory
            results = search_memory(self.query, top_k=self.top_k)
            self.done.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class ResultCard(QFrame):
    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame{background:#161b22; border:1px solid #30363d; border-radius:8px;}"
            "QFrame:hover{border-color:#58a6ff;}"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        meta = result.get("metadata", {})
        topic = meta.get("topic_name", "")
        date = meta.get("date", "")
        role = meta.get("role", "")
        dist = result.get("distance", 1.0)
        score = max(0, int((1 - dist) * 100))

        # 头部
        header = QHBoxLayout()
        topic_lbl = QLabel(f"📁 {topic}" if topic else "📁 未知话题")
        topic_lbl.setStyleSheet("color:#58a6ff; font-weight:bold;")
        header.addWidget(topic_lbl)
        header.addStretch()
        meta_lbl = QLabel(f"{date}  相关度 {score}%")
        meta_lbl.setStyleSheet("color:#484f58; font-size:12px;")
        header.addWidget(meta_lbl)
        layout.addLayout(header)

        # 角色标签
        role_map = {"user": "我说", "assistant": "AI", "insight": "洞察"}
        if role:
            role_lbl = QLabel(role_map.get(role, role))
            role_lbl.setStyleSheet(
                "background:#21262d; color:#8b949e; font-size:11px; "
                "padding:1px 6px; border-radius:3px;"
            )
            role_lbl.setFixedHeight(18)
            role_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            layout.addWidget(role_lbl)

        # 文本摘要
        text = result.get("text", "")
        snippet = text[:280] + ("…" if len(text) > 280 else "")
        text_lbl = QLabel(snippet)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet("color:#c9d1d9; font-size:13px;")
        layout.addWidget(text_lbl)


class SearchPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: SearchWorker | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("记忆搜索")
        title.setStyleSheet("font-size:18px; font-weight:bold; color:#e6edf3;")
        layout.addWidget(title)

        # 搜索栏
        search_row = QHBoxLayout()
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("输入关键词或描述，语义搜索历史记忆…")
        self.query_edit.returnPressed.connect(self._search)
        search_row.addWidget(self.query_edit, 1)

        self.topk_box = QComboBox()
        for n in [5, 10, 20, 50]:
            self.topk_box.addItem(f"Top {n}", n)
        self.topk_box.setFixedWidth(90)
        search_row.addWidget(self.topk_box)

        self.search_btn = QPushButton("搜索")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.clicked.connect(self._search)
        search_row.addWidget(self.search_btn)
        layout.addLayout(search_row)

        self.status_lbl = QLabel("在记忆库中搜索相关思考内容")
        self.status_lbl.setObjectName("sectionLabel")
        layout.addWidget(self.status_lbl)

        # 结果列表
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.result_container = QWidget()
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setSpacing(8)
        self.result_layout.addStretch()

        self.scroll.setWidget(self.result_container)
        layout.addWidget(self.scroll, 1)

    def _search(self):
        query = self.query_edit.text().strip()
        if not query or self._worker:
            return

        top_k = self.topk_box.currentData()
        self.search_btn.setEnabled(False)
        self.status_lbl.setText("搜索中…")

        self._worker = SearchWorker(query, top_k)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, results: list):
        self._worker = None
        self.search_btn.setEnabled(True)

        # 清空旧结果
        while self.result_layout.count() > 1:
            item = self.result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not results:
            self.status_lbl.setText("未找到相关记忆")
            return

        self.status_lbl.setText(f"找到 {len(results)} 条相关记忆")
        for r in results:
            card = ResultCard(r)
            self.result_layout.insertWidget(self.result_layout.count() - 1, card)

    def _on_error(self, msg: str):
        self._worker = None
        self.search_btn.setEnabled(True)
        self.status_lbl.setText(f"搜索失败：{msg}")
