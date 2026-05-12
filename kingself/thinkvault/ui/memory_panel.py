"""记忆库管理面板：浏览 AI 已学习到的全部内容，可删除。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QComboBox,
    QSizePolicy, QMessageBox, QLineEdit,
)

from core.memory import memory_count


ROLE_LABELS = {
    "user":      ("我说", "#1f6feb"),
    "assistant": ("AI",   "#3fb950"),
    "note":      ("笔记", "#e3b341"),
    "insight":   ("洞察", "#a371f7"),
    "report":    ("报告", "#f0883e"),
}


class LoadWorker(QThread):
    done = Signal(list)
    error = Signal(str)

    def __init__(self, query: str, top_k: int, role_filter: str | None):
        super().__init__()
        self.query = query
        self.top_k = top_k
        self.role_filter = role_filter

    def run(self):
        try:
            from core.memory import search_memory
            where = None
            if self.role_filter:
                where = {"role": self.role_filter}
            results = search_memory(self.query or "思维 经验 知识", top_k=self.top_k, where=where)
            self.done.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class MemoryCard(QFrame):
    delete_requested = Signal(str)

    def __init__(self, result: dict, parent=None):
        super().__init__(parent)
        self.doc_id = result["id"]
        meta = result.get("metadata", {})
        role = meta.get("role", "")
        label, color = ROLE_LABELS.get(role, (role, "#8b949e"))
        dist = result.get("distance", 1.0)
        score = max(0, int((1 - dist) * 100))

        self.setStyleSheet(
            f"QFrame{{background:#161b22; border:1px solid #30363d; border-left:3px solid {color}; border-radius:6px;}}"
            "QFrame:hover{border-color:#58a6ff;border-left-color:" + color + ";}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()

        role_lbl = QLabel(label)
        role_lbl.setStyleSheet(
            f"background:{color}22; color:{color}; font-size:11px; "
            "padding:1px 6px; border-radius:3px; font-weight:bold;"
        )
        role_lbl.setFixedHeight(18)
        role_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        header.addWidget(role_lbl)

        topic = meta.get("topic_name", "")
        if topic:
            topic_lbl = QLabel(topic)
            topic_lbl.setStyleSheet("color:#8b949e; font-size:12px; margin-left:6px;")
            header.addWidget(topic_lbl)

        header.addStretch()

        date_lbl = QLabel(f"{meta.get('date','')}  相关度 {score}%")
        date_lbl.setStyleSheet("color:#484f58; font-size:11px;")
        header.addWidget(date_lbl)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#484f58;border:none;font-size:14px;}"
            "QPushButton:hover{color:#f85149;}"
        )
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.doc_id))
        header.addWidget(del_btn)
        layout.addLayout(header)

        text = result.get("text", "")
        snippet = text[:300] + ("…" if len(text) > 300 else "")
        text_lbl = QLabel(snippet)
        text_lbl.setWordWrap(True)
        text_lbl.setStyleSheet("color:#8b949e; font-size:13px;")
        layout.addWidget(text_lbl)


class MemoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: LoadWorker | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 标题行
        title_row = QHBoxLayout()
        title_lbl = QLabel("记忆库")
        title_lbl.setStyleSheet("font-size:18px; font-weight:bold; color:#e6edf3;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        self.total_lbl = QLabel()
        self.total_lbl.setStyleSheet("color:#58a6ff; font-size:13px;")
        title_row.addWidget(self.total_lbl)
        layout.addLayout(title_row)

        hint = QLabel("AI 对话时会自动从这里检索相关内容，引用到回答中")
        hint.setStyleSheet("color:#484f58; font-size:12px;")
        layout.addWidget(hint)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#21262d; border:none; max-height:1px;")
        layout.addWidget(sep)

        # 搜索 + 筛选行
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("输入关键词搜索记忆内容…")
        self.query_edit.returnPressed.connect(self.refresh)
        ctrl_row.addWidget(self.query_edit, 1)

        self.role_box = QComboBox()
        self.role_box.addItem("全部类型", None)
        for role, (label, _) in ROLE_LABELS.items():
            self.role_box.addItem(label, role)
        self.role_box.setFixedWidth(90)
        ctrl_row.addWidget(self.role_box)

        self.topk_box = QComboBox()
        for n in [20, 50, 100]:
            self.topk_box.addItem(f"显示 {n}", n)
        self.topk_box.setFixedWidth(90)
        ctrl_row.addWidget(self.topk_box)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("primaryBtn")
        refresh_btn.clicked.connect(self.refresh)
        ctrl_row.addWidget(refresh_btn)
        layout.addLayout(ctrl_row)

        self.status_lbl = QLabel("点击「刷新」加载记忆库内容")
        self.status_lbl.setObjectName("sectionLabel")
        layout.addWidget(self.status_lbl)

        # 卡片列表
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll.setWidget(self.cards_container)
        layout.addWidget(self.scroll, 1)

        self._update_total()

    def _update_total(self):
        try:
            cnt = memory_count()
            self.total_lbl.setText(f"共 {cnt} 条记忆")
        except Exception:
            self.total_lbl.setText("")

    def refresh(self):
        if self._worker:
            return
        query = self.query_edit.text().strip()
        top_k = self.topk_box.currentData()
        role_filter = self.role_box.currentData()

        self.status_lbl.setText("加载中…")
        self._worker = LoadWorker(query, top_k, role_filter)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, results: list):
        self._worker = None
        self._render(results)
        self._update_total()

    def _on_error(self, msg: str):
        self._worker = None
        self.status_lbl.setText(f"加载失败：{msg}")

    def _render(self, results: list):
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.status_lbl.setText(f"显示 {len(results)} 条")
        for r in results:
            card = MemoryCard(r)
            card.delete_requested.connect(self._delete_memory)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _delete_memory(self, doc_id: str):
        reply = QMessageBox.question(
            self, "删除记忆",
            f"确认从记忆库中删除这条记忆？\nID: {doc_id}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                from core.memory import delete_memory
                delete_memory(doc_id)
            except Exception as e:
                QMessageBox.warning(self, "删除失败", str(e))
                return
            self.refresh()
