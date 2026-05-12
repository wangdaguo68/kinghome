"""主窗口：整合侧边栏 + 标签页内容区。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QTabWidget, QStatusBar, QLabel, QFrame,
)

from ui.sidebar import SidebarPanel
from ui.chat_panel import ChatPanel
from ui.notes_panel import NotesPanel
from ui.memory_panel import MemoryPanel
from ui.search_panel import SearchPanel
from ui.report_panel import ReportPanel
from ui.style import STYLE


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ThinkVault — 我的数字分身")
        self.resize(1280, 800)
        self.setMinimumSize(960, 620)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._build_menubar()
        self._build_statusbar()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 侧边栏
        self.sidebar = SidebarPanel()
        self.sidebar.topic_selected.connect(self._on_topic_selected)
        self.sidebar.topic_deleted.connect(self._on_topic_deleted)
        outer.addWidget(self.sidebar)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background:#21262d; border:none; max-width:1px;")
        outer.addWidget(sep)

        # 右侧标签页
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # ① 对话（数字分身）
        self.chat_panel = ChatPanel()
        self.chat_panel.status_message.connect(self.statusBar().showMessage)
        self.tabs.addTab(self.chat_panel, "💬  对话分身")

        # ② 笔记（无 AI，直接喂内容）
        self.notes_panel = NotesPanel()
        self.notes_panel.memory_updated.connect(self._on_memory_updated)
        self.tabs.addTab(self.notes_panel, "📝  记录内容")

        # ③ 记忆库浏览
        self.memory_panel = MemoryPanel()
        self.tabs.addTab(self.memory_panel, "🧠  记忆库")

        # ④ 语义搜索
        self.search_panel = SearchPanel()
        self.tabs.addTab(self.search_panel, "🔍  搜索")

        # ⑤ 学习报告
        self.report_panel = ReportPanel()
        self.tabs.addTab(self.report_panel, "📊  学习报告")

        outer.addWidget(self.tabs, 1)

    def _build_menubar(self):
        menu = self.menuBar()
        menu.setStyleSheet(
            "QMenuBar{background:#010409; color:#8b949e; border-bottom:1px solid #21262d;}"
            "QMenuBar::item:selected{background:#161b22; color:#e6edf3;}"
        )

        file_menu = menu.addMenu("文件")
        new_topic = QAction("新建对话话题  Ctrl+N", self)
        new_topic.setShortcut(QKeySequence("Ctrl+N"))
        new_topic.triggered.connect(self.sidebar._new_topic)
        file_menu.addAction(new_topic)

        new_note = QAction("快速记录  Ctrl+Shift+N", self)
        new_note.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_note.triggered.connect(self._go_notes)
        file_menu.addAction(new_note)

        file_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        settings_action = QAction("设置  Ctrl+,", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        menu.addAction(settings_action)

        help_menu = menu.addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    def _build_statusbar(self):
        sb = QStatusBar()
        sb.showMessage("就绪  ·  先去「记录内容」喂给 AI，再来「对话分身」")
        self.setStatusBar(sb)

        self.mem_count_lbl = QLabel()
        self.mem_count_lbl.setStyleSheet("color:#484f58; font-size:12px; padding-right:8px;")
        sb.addPermanentWidget(self.mem_count_lbl)
        self._update_mem_count()

    def _update_mem_count(self):
        try:
            from core.memory import memory_count
            cnt = memory_count()
            self.mem_count_lbl.setText(f"记忆库  {cnt} 条")
        except Exception:
            self.mem_count_lbl.setText("")

    def _on_memory_updated(self):
        self._update_mem_count()
        self.sidebar._update_mem_label()

    def _on_topic_selected(self, topic_id: int, topic_name: str):
        self.chat_panel.load_topic(topic_id, topic_name)
        self.tabs.setCurrentIndex(0)
        self.statusBar().showMessage(f"已切换到：{topic_name}")

    def _on_topic_deleted(self, topic_id: int):
        if self.chat_panel.topic_id == topic_id:
            self.chat_panel.clear_topic()
        self._update_mem_count()

    def _go_notes(self):
        self.tabs.setCurrentIndex(1)
        self.notes_panel.content_edit.setFocus()

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.statusBar().showMessage("设置已保存")

    def _about(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(
            self, "关于 ThinkVault",
            "<b>ThinkVault — 我的数字分身</b> v1.1<br><br>"
            "工作流程：<br>"
            "① <b>记录内容</b> — 把经历、观点、规律、知识写进来，无需 AI<br>"
            "② <b>记忆库</b> — 查看 AI 已学习到的全部内容<br>"
            "③ <b>对话分身</b> — AI 以你的思维方式回答问题<br>"
            "④ <b>学习报告</b> — 发现思维规律<br><br>"
            "数据全部存储在本地，保护隐私。",
        )
