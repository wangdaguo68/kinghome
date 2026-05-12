"""对话面板：消息气泡 + 流式输出 + RAG 引用标记。"""

from __future__ import annotations

import textwrap
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QTimer, QSize
from PySide6.QtGui import QKeyEvent, QFont, QTextCursor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QSizePolicy,
    QFrame, QSpacerItem,
)

import core.database as db
from core.ai_client import chat_stream


# ── AI 工作线程 ────────────────────────────────────────────────────────────────

class AIChatWorker(QThread):
    token = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, messages: list[dict], user_input: str):
        super().__init__()
        self.messages = messages
        self.user_input = user_input

    def run(self):
        try:
            for tok in chat_stream(self.messages, self.user_input):
                self.token.emit(tok)
            self.finished.emit()
        except RuntimeError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"未知错误：{e}")


# ── 单条消息气泡 ────────────────────────────────────────────────────────────────

class MessageBubble(QWidget):
    def __init__(self, role: str, content: str, ts: str = "", parent=None):
        super().__init__(parent)
        self.role = role
        self._build(role, content, ts)

    def _build(self, role: str, content: str, ts: str):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 4, 12, 4)
        outer.setSpacing(0)

        bubble = QFrame()
        bubble.setObjectName("msgUser" if role == "user" else "msgAssistant")
        bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        inner = QVBoxLayout(bubble)
        inner.setContentsMargins(12, 8, 12, 8)
        inner.setSpacing(4)

        # 角色标签 + 时间
        header = QHBoxLayout()
        role_label = QLabel("我" if role == "user" else "AI")
        role_label.setObjectName("msgRole")
        header.addWidget(role_label)
        header.addStretch()
        if ts:
            time_label = QLabel(ts[:16])
            time_label.setObjectName("msgTime")
            header.addWidget(time_label)
        inner.addLayout(header)

        # 消息内容（可选中文本）
        self.content_label = QTextEdit()
        self.content_label.setReadOnly(True)
        self.content_label.setFrameStyle(QFrame.NoFrame)
        self.content_label.setStyleSheet(
            "background:transparent; border:none; padding:0; color:#e6edf3;"
        )
        self.content_label.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_label.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_label.setMarkdown(content) if content else None
        self.content_label.document().contentsChanged.connect(self._adjust_height)
        self._adjust_height()
        inner.addWidget(self.content_label)

        if role == "user":
            outer.addSpacerItem(QSpacerItem(60, 0, QSizePolicy.Minimum, QSizePolicy.Minimum))
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addSpacerItem(QSpacerItem(60, 0, QSizePolicy.Minimum, QSizePolicy.Minimum))

    def _adjust_height(self):
        doc = self.content_label.document()
        doc.setTextWidth(self.content_label.viewport().width())
        h = int(doc.size().height()) + 4
        self.content_label.setFixedHeight(max(h, 20))

    def append_text(self, text: str):
        cursor = self.content_label.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self._adjust_height()

    def set_markdown(self, md: str):
        self.content_label.setMarkdown(md)
        self._adjust_height()


# ── 对话面板 ───────────────────────────────────────────────────────────────────

class ChatPanel(QWidget):
    status_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.topic_id: Optional[int] = None
        self.topic_name: str = ""
        self._messages: list[dict] = []   # OpenAI 格式历史
        self._worker: Optional[AIChatWorker] = None
        self._current_bubble: Optional[MessageBubble] = None
        self._current_ai_text: str = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        self.title_bar = self._build_title_bar()
        layout.addWidget(self.title_bar)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#21262d; border:none; max-height:1px;")
        layout.addWidget(sep)

        # 消息区域（可滚动）
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("chatArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.msg_container = QWidget()
        self.msg_container.setObjectName("chatArea")
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(0, 8, 0, 8)
        self.msg_layout.setSpacing(4)
        self.msg_layout.addStretch()

        self.scroll_area.setWidget(self.msg_container)
        layout.addWidget(self.scroll_area, 1)

        # 占位提示
        self.placeholder = self._build_placeholder()
        layout.addWidget(self.placeholder)

        # 输入区
        input_frame = self._build_input_area()
        layout.addWidget(input_frame)

        self._show_placeholder(True)

    def _build_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background:#010409;")
        bar.setFixedHeight(48)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 0, 12, 0)

        self.title_label = QLabel("请选择或新建一个话题")
        self.title_label.setStyleSheet("font-size:15px; font-weight:bold; color:#e6edf3;")
        h.addWidget(self.title_label)
        h.addStretch()

        self.insight_btn = QPushButton("生成洞察")
        self.insight_btn.setEnabled(False)
        self.insight_btn.clicked.connect(self._generate_insight)
        h.addWidget(self.insight_btn)

        self.clear_btn = QPushButton("清空")
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self._clear_chat)
        h.addWidget(self.clear_btn)

        return bar

    def _build_placeholder(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignCenter)
        lbl = QLabel("选择一个话题开始记录思考\n或点击「＋ 新建话题」创建新的思维空间")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color:#484f58; font-size:15px; line-height:1.8;")
        v.addWidget(lbl)
        return w

    def _build_input_area(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet("background:#010409; border-top:1px solid #21262d;")
        h = QHBoxLayout(frame)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(8)

        self.input_edit = InputTextEdit()
        self.input_edit.setPlaceholderText("输入你的想法… (Enter 发送，Shift+Enter 换行)")
        self.input_edit.setMinimumHeight(44)
        self.input_edit.setMaximumHeight(160)
        self.input_edit.send_requested.connect(self._send)
        h.addWidget(self.input_edit, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setObjectName("primaryBtn")
        self.send_btn.setFixedWidth(72)
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._send)
        h.addWidget(self.send_btn)

        return frame

    # ── 公开接口 ────────────────────────────────────────────────────────────────

    def load_topic(self, topic_id: int, topic_name: str):
        self.topic_id = topic_id
        self.topic_name = topic_name
        self.title_label.setText(topic_name)
        self.send_btn.setEnabled(True)
        self.insight_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self._show_placeholder(False)
        self._reload_messages()

    def _reload_messages(self):
        # 清空气泡
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = db.get_messages(self.topic_id)
        self._messages = []
        for row in rows:
            self._add_bubble(row["role"], row["content"], row["created_at"])
            self._messages.append({"role": row["role"], "content": row["content"]})

        QTimer.singleShot(50, self._scroll_bottom)

    def clear_topic(self):
        self.topic_id = None
        self.topic_name = ""
        self.title_label.setText("请选择或新建一个话题")
        self.send_btn.setEnabled(False)
        self.insight_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self._show_placeholder(True)
        self._messages.clear()
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ── 发送消息 ────────────────────────────────────────────────────────────────

    def _send(self):
        if not self.topic_id or self._worker:
            return
        text = self.input_edit.toPlainText().strip()
        if not text:
            return

        self.input_edit.clear()
        self.send_btn.setEnabled(False)

        # 显示用户气泡
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._add_bubble("user", text, ts)
        mid = db.add_message(self.topic_id, "user", text)

        # 存入记忆库
        self._store_memory(f"msg_{mid}", text, "user")

        self._messages.append({"role": "user", "content": text})

        # 创建 AI 气泡（占位）
        self._current_ai_text = ""
        ai_bubble = MessageBubble("assistant", "…", "")
        self._current_bubble = ai_bubble
        self._insert_bubble(ai_bubble)
        self._scroll_bottom()

        # 启动 AI 线程
        self._worker = AIChatWorker(list(self._messages), text)
        self._worker.token.connect(self._on_token)
        self._worker.finished.connect(self._on_ai_done)
        self._worker.error.connect(self._on_ai_error)
        self._worker.start()
        self.status_message.emit("AI 思考中…")

    def _on_token(self, tok: str):
        self._current_ai_text += tok
        if self._current_bubble:
            self._current_bubble.append_text(tok)
        self._scroll_bottom()

    def _on_ai_done(self):
        self._worker = None
        self.send_btn.setEnabled(True)

        final_text = self._current_ai_text
        if self._current_bubble and final_text:
            self._current_bubble.set_markdown(final_text)

        if final_text:
            mid = db.add_message(self.topic_id, "assistant", final_text)
            self._store_memory(f"msg_{mid}", final_text, "assistant")
            self._messages.append({"role": "assistant", "content": final_text})

        self._current_bubble = None
        self._current_ai_text = ""
        self.status_message.emit("就绪")
        self._scroll_bottom()

    def _on_ai_error(self, msg: str):
        self._worker = None
        self.send_btn.setEnabled(True)
        if self._current_bubble:
            self._current_bubble.set_markdown(f"⚠️ {msg}")
        self._current_bubble = None
        self._current_ai_text = ""
        self.status_message.emit(f"错误：{msg}")

    # ── 辅助方法 ────────────────────────────────────────────────────────────────

    def _add_bubble(self, role: str, content: str, ts: str):
        bubble = MessageBubble(role, content, ts)
        self._insert_bubble(bubble)

    def _insert_bubble(self, bubble: MessageBubble):
        # 插在 stretch 之前
        self.msg_layout.insertWidget(self.msg_layout.count() - 1, bubble)

    def _scroll_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def _show_placeholder(self, show: bool):
        self.placeholder.setVisible(show)
        self.scroll_area.setVisible(not show)

    def _store_memory(self, doc_id: str, text: str, role: str):
        try:
            from core.memory import add_memory
            add_memory(
                doc_id=doc_id,
                text=text,
                metadata={
                    "topic_id":   str(self.topic_id),
                    "topic_name": self.topic_name,
                    "role":       role,
                    "date":       datetime.now().strftime("%Y-%m-%d"),
                },
            )
        except Exception:
            pass

    def _generate_insight(self):
        if not self.topic_id or not self._messages:
            return
        from ui.insight_dialog import InsightDialog
        dlg = InsightDialog(self.topic_id, self.topic_name, self._messages, self)
        dlg.exec()

    def _clear_chat(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "清空对话",
            "确认清空当前话题的所有对话记录？（记忆库中的内容不会删除）",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from core.database import get_conn
            with get_conn() as conn:
                conn.execute("DELETE FROM messages WHERE topic_id=?", (self.topic_id,))
            self._messages.clear()
            while self.msg_layout.count() > 1:
                item = self.msg_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()


# ── 自定义输入框（Enter 发送）─────────────────────────────────────────────────

class InputTextEdit(QTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
            self.send_requested.emit()
        else:
            super().keyPressEvent(event)
