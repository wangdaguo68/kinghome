"""左侧话题列表面板。"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QLineEdit,
    QMenu, QInputDialog, QMessageBox,
)

import core.database as db


class SidebarPanel(QWidget):
    topic_selected = Signal(int, str)   # topic_id, topic_name
    topic_deleted = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        # 标题
        title = QLabel("ThinkVault")
        title.setStyleSheet("font-size:16px; font-weight:bold; color:#58a6ff; padding:4px 4px 8px;")
        layout.addWidget(title)

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索话题…")
        self.search_edit.textChanged.connect(self._filter)
        layout.addWidget(self.search_edit)

        # 新建按钮
        new_btn = QPushButton("＋  新建话题")
        new_btn.setObjectName("newTopicBtn")
        new_btn.clicked.connect(self._new_topic)
        layout.addWidget(new_btn)

        # 话题列表
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("topicList")
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget, 1)

        # 底部记忆统计
        self.mem_label = QLabel()
        self.mem_label.setObjectName("sectionLabel")
        self.mem_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.mem_label)

    def refresh(self):
        """重新从数据库加载话题列表。"""
        self._all_topics = db.get_topics()
        self._render(self._all_topics)
        self._update_mem_label()

    def _update_mem_label(self):
        try:
            from core.memory import memory_count
            cnt = memory_count()
            self.mem_label.setText(f"记忆库  {cnt} 条")
        except Exception:
            self.mem_label.setText("记忆库")

    def _render(self, topics: list[dict]):
        self.list_widget.clear()
        for t in topics:
            item = QListWidgetItem(self._format_name(t))
            item.setData(Qt.UserRole, t["id"])
            item.setData(Qt.UserRole + 1, t["name"])
            item.setToolTip(t["updated_at"][:16] if t.get("updated_at") else "")
            self.list_widget.addItem(item)

    def _format_name(self, t: dict) -> str:
        name = t["name"]
        if len(name) > 18:
            name = name[:18] + "…"
        return name

    def _filter(self, text: str):
        keyword = text.strip().lower()
        if not keyword:
            self._render(self._all_topics)
            return
        filtered = [t for t in self._all_topics if keyword in t["name"].lower()]
        self._render(filtered)

    def _on_item_clicked(self, item: QListWidgetItem):
        topic_id = item.data(Qt.UserRole)
        topic_name = item.data(Qt.UserRole + 1)
        self.topic_selected.emit(topic_id, topic_name)

    def _new_topic(self):
        name, ok = QInputDialog.getText(self, "新建话题", "话题名称：")
        if ok and name.strip():
            tid = db.create_topic(name.strip())
            self.refresh()
            # 自动选中新话题
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item.data(Qt.UserRole) == tid:
                    self.list_widget.setCurrentItem(item)
                    self.topic_selected.emit(tid, name.strip())
                    break

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        topic_id = item.data(Qt.UserRole)
        topic_name = item.data(Qt.UserRole + 1)

        menu = QMenu(self)
        rename_action = QAction("重命名", self)
        delete_action = QAction("删除话题", self)
        menu.addAction(rename_action)
        menu.addSeparator()
        menu.addAction(delete_action)

        rename_action.triggered.connect(lambda: self._rename_topic(topic_id, topic_name))
        delete_action.triggered.connect(lambda: self._delete_topic(topic_id, topic_name))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def _rename_topic(self, topic_id: int, old_name: str):
        name, ok = QInputDialog.getText(self, "重命名话题", "新名称：", text=old_name)
        if ok and name.strip():
            db.rename_topic(topic_id, name.strip())
            self.refresh()

    def _delete_topic(self, topic_id: int, name: str):
        reply = QMessageBox.question(
            self, "删除话题",
            f"确认删除「{name}」及其所有对话记录？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            try:
                from core.memory import delete_topic_memories
                delete_topic_memories(topic_id)
            except Exception:
                pass
            db.delete_topic(topic_id)
            self.topic_deleted.emit(topic_id)
            self.refresh()

    def select_topic(self, topic_id: int):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.data(Qt.UserRole) == topic_id:
                self.list_widget.setCurrentItem(item)
                return
