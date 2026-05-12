"""笔记面板：无需 AI，直接往记忆库写内容。"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QComboBox,
    QListWidget, QListWidgetItem, QSplitter,
    QFrame, QSizePolicy, QMessageBox,
)

import core.database as db

CATEGORIES = ["经历", "观点", "规律", "知识", "情绪", "计划", "其他"]

CATEGORY_COLORS = {
    "经历": "#1f6feb",
    "观点": "#388bfd",
    "规律": "#3fb950",
    "知识": "#e3b341",
    "情绪": "#f85149",
    "计划": "#a371f7",
    "其他": "#8b949e",
}


class EmbedWorker(QThread):
    done = Signal(str)
    error = Signal(str)

    def __init__(self, note_id: int, text: str, title: str, category: str):
        super().__init__()
        self.note_id = note_id
        self.text = text
        self.title = title
        self.category = category

    def run(self):
        try:
            from core.memory import add_memory
            embed_text = f"[{self.category}] {self.title}\n{self.text}" if self.title else f"[{self.category}] {self.text}"
            add_memory(
                doc_id=f"note_{self.note_id}",
                text=embed_text,
                metadata={
                    "topic_id":   "0",
                    "topic_name": f"笔记/{self.category}",
                    "role":       "note",
                    "category":   self.category,
                    "title":      self.title,
                    "date":       datetime.now().strftime("%Y-%m-%d"),
                },
            )
            self.done.emit(f"已存入记忆库 · {self.category}")
        except Exception as e:
            self.error.emit(str(e))


class NoteCard(QFrame):
    delete_requested = Signal(int)

    def __init__(self, note: dict, parent=None):
        super().__init__(parent)
        self.note_id = note["id"]
        color = CATEGORY_COLORS.get(note["category"], "#8b949e")
        self.setStyleSheet(
            f"QFrame{{background:#161b22; border:1px solid #30363d; border-left:3px solid {color}; border-radius:6px;}}"
            "QFrame:hover{border-color:#58a6ff;border-left-color:" + color + ";}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 头部
        header = QHBoxLayout()
        cat_lbl = QLabel(note["category"])
        cat_lbl.setStyleSheet(
            f"background:{color}22; color:{color}; font-size:11px; "
            "padding:1px 6px; border-radius:3px; font-weight:bold;"
        )
        cat_lbl.setFixedHeight(18)
        cat_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        header.addWidget(cat_lbl)

        if note.get("title"):
            title_lbl = QLabel(note["title"])
            title_lbl.setStyleSheet("color:#e6edf3; font-weight:bold; margin-left:6px;")
            header.addWidget(title_lbl)

        header.addStretch()

        date_lbl = QLabel(note["created_at"][:10])
        date_lbl.setStyleSheet("color:#484f58; font-size:11px;")
        header.addWidget(date_lbl)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#484f58;border:none;font-size:14px;}"
            "QPushButton:hover{color:#f85149;}"
        )
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.note_id))
        header.addWidget(del_btn)
        layout.addLayout(header)

        # 内容摘要
        snippet = note["content"][:200] + ("…" if len(note["content"]) > 200 else "")
        content_lbl = QLabel(snippet)
        content_lbl.setWordWrap(True)
        content_lbl.setStyleSheet("color:#8b949e; font-size:13px;")
        layout.addWidget(content_lbl)


class NotesPanel(QWidget):
    memory_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list[EmbedWorker] = []
        self._build_ui()
        self._load_notes()

    def _build_ui(self):
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle{background:#21262d;}")

        # ── 上半部分：输入区 ──
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(16, 16, 16, 12)
        input_layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_lbl = QLabel("记录新内容")
        title_lbl.setStyleSheet("font-size:16px; font-weight:bold; color:#e6edf3;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        hint = QLabel("不需要 AI，直接写，存入记忆库供 AI 学习")
        hint.setStyleSheet("color:#484f58; font-size:12px;")
        title_row.addWidget(hint)
        input_layout.addLayout(title_row)

        # 分类 + 标题行
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)

        self.cat_box = QComboBox()
        for cat in CATEGORIES:
            self.cat_box.addItem(cat)
        self.cat_box.setFixedWidth(90)
        meta_row.addWidget(QLabel("分类:"))
        meta_row.addWidget(self.cat_box)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("标题（可选）")
        meta_row.addWidget(self.title_edit, 1)
        input_layout.addLayout(meta_row)

        # 内容区
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText(
            "写下你的经历、观点、规律、知识…\n\n"
            "这里的内容会被向量化存入记忆库，AI 对话时会引用这些内容，\n"
            "逐渐学习你的思维方式。"
        )
        self.content_edit.setMinimumHeight(160)
        input_layout.addWidget(self.content_edit, 1)

        # 保存按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.char_lbl = QLabel("0 字")
        self.char_lbl.setStyleSheet("color:#484f58; font-size:12px;")
        self.content_edit.textChanged.connect(
            lambda: self.char_lbl.setText(f"{len(self.content_edit.toPlainText())} 字")
        )
        btn_row.addWidget(self.char_lbl)

        self.save_btn = QPushButton("存入记忆库")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self._save_note)
        btn_row.addWidget(self.save_btn)
        input_layout.addLayout(btn_row)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color:#3fb950; font-size:12px;")
        self.status_lbl.setAlignment(Qt.AlignRight)
        input_layout.addWidget(self.status_lbl)

        splitter.addWidget(input_widget)

        # ── 下半部分：历史记录 ──
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(16, 8, 16, 16)
        history_layout.setSpacing(8)

        filter_row = QHBoxLayout()
        hist_title = QLabel("已记录内容")
        hist_title.setStyleSheet("font-size:14px; font-weight:bold; color:#c9d1d9;")
        filter_row.addWidget(hist_title)
        filter_row.addStretch()

        self.filter_box = QComboBox()
        self.filter_box.addItem("全部", None)
        for cat in CATEGORIES:
            self.filter_box.addItem(cat, cat)
        self.filter_box.setFixedWidth(90)
        self.filter_box.currentIndexChanged.connect(self._load_notes)
        filter_row.addWidget(QLabel("筛选:"))
        filter_row.addWidget(self.filter_box)

        self.count_lbl = QLabel("")
        self.count_lbl.setStyleSheet("color:#484f58; font-size:12px;")
        filter_row.addWidget(self.count_lbl)
        history_layout.addLayout(filter_row)

        from PySide6.QtWidgets import QScrollArea
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll.setWidget(self.cards_container)
        history_layout.addWidget(self.scroll, 1)

        splitter.addWidget(history_widget)
        splitter.setSizes([420, 320])

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(splitter)

    def _save_note(self):
        content = self.content_edit.toPlainText().strip()
        if not content:
            return

        title = self.title_edit.text().strip()
        category = self.cat_box.currentText()

        note_id = db.add_note(content, title, category)
        self.content_edit.clear()
        self.title_edit.clear()
        self.status_lbl.setText("向量化中，请稍候…")
        self.save_btn.setEnabled(False)

        worker = EmbedWorker(note_id, content, title, category)
        worker.done.connect(self._on_embed_done)
        worker.error.connect(self._on_embed_error)
        self._workers.append(worker)
        worker.start()

        self._load_notes()

    def _on_embed_done(self, msg: str):
        self.status_lbl.setText(f"✓ {msg}")
        self.save_btn.setEnabled(True)
        self.memory_updated.emit()

    def _on_embed_error(self, msg: str):
        self.status_lbl.setText(f"⚠ 向量化失败：{msg}")
        self.save_btn.setEnabled(True)

    def _load_notes(self):
        category = self.filter_box.currentData()
        notes = db.get_notes(limit=200, category=category)
        self.count_lbl.setText(f"共 {len(notes)} 条")

        # 清空卡片
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for note in notes:
            card = NoteCard(note)
            card.delete_requested.connect(self._delete_note)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _delete_note(self, note_id: int):
        reply = QMessageBox.question(
            self, "删除记录",
            "确认删除这条记录？（记忆库中对应的向量也会删除）",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                from core.memory import delete_memory
                delete_memory(f"note_{note_id}")
            except Exception:
                pass
            db.delete_note(note_id)
            self._load_notes()
            self.memory_updated.emit()
