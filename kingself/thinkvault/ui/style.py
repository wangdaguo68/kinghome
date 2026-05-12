"""全局暗色主题 stylesheet。"""

STYLE = """
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
}

/* ── 滚动条 ── */
QScrollBar:vertical {
    background: #161b22;
    width: 6px;
    margin: 0;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #58a6ff; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #161b22;
    height: 6px;
    border-radius: 3px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: #58a6ff; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── 侧边栏 ── */
#sidebar {
    background-color: #010409;
    border-right: 1px solid #21262d;
}

#sidebar QPushButton#newTopicBtn {
    background-color: #238636;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 8px;
    font-weight: bold;
}
#sidebar QPushButton#newTopicBtn:hover { background-color: #2ea043; }
#sidebar QPushButton#newTopicBtn:pressed { background-color: #196127; }

#topicList {
    background-color: transparent;
    border: none;
    outline: none;
}
#topicList::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 1px 4px;
    color: #8b949e;
}
#topicList::item:hover { background-color: #161b22; color: #e6edf3; }
#topicList::item:selected { background-color: #1f2937; color: #58a6ff; }

/* ── 搜索框 ── */
QLineEdit {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e6edf3;
}
QLineEdit:focus { border-color: #58a6ff; }
QLineEdit::placeholder { color: #484f58; }

/* ── 普通按钮 ── */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 12px;
}
QPushButton:hover { background-color: #30363d; color: #e6edf3; border-color: #58a6ff; }
QPushButton:pressed { background-color: #161b22; }
QPushButton:disabled { color: #484f58; border-color: #21262d; }

/* ── 主要强调按钮 ── */
QPushButton#primaryBtn {
    background-color: #1f6feb;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton#primaryBtn:hover { background-color: #388bfd; }
QPushButton#primaryBtn:pressed { background-color: #1158c7; }

/* ── 输入区域 ── */
QTextEdit {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px;
    color: #e6edf3;
    selection-background-color: #1f6feb;
}
QTextEdit:focus { border-color: #58a6ff; }

/* ── 标签页 ── */
QTabWidget::pane {
    border: none;
    background-color: #0d1117;
}
QTabBar::tab {
    background-color: #010409;
    color: #8b949e;
    padding: 8px 20px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #e6edf3;
    border-bottom: 2px solid #58a6ff;
    background-color: #0d1117;
}
QTabBar::tab:hover:!selected { color: #c9d1d9; background-color: #161b22; }

/* ── 分割线 ── */
QSplitter::handle { background-color: #21262d; }
QSplitter::handle:horizontal { width: 1px; }

/* ── 弹出菜单 ── */
QMenu {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item { padding: 6px 20px; border-radius: 4px; }
QMenu::item:selected { background-color: #1f2937; color: #e6edf3; }
QMenu::separator { height: 1px; background-color: #30363d; margin: 4px 0; }

/* ── 对话框 ── */
QDialog {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
}

/* ── ComboBox ── */
QComboBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 10px;
    color: #e6edf3;
}
QComboBox:hover { border-color: #58a6ff; }
QComboBox::drop-down { border: none; padding-right: 6px; }
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #1f2937;
}

/* ── 标签 ── */
QLabel#sectionLabel {
    color: #8b949e;
    font-size: 12px;
    font-weight: bold;
    padding: 4px 0;
}

/* ── 状态栏 ── */
QStatusBar {
    background-color: #010409;
    color: #8b949e;
    border-top: 1px solid #21262d;
    font-size: 12px;
}

/* ── 工具提示 ── */
QToolTip {
    background-color: #161b22;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
}

/* ── 消息气泡容器 ── */
#chatArea { background-color: #0d1117; }
#msgUser {
    background-color: #1f3a5f;
    border-radius: 12px;
    border-bottom-right-radius: 3px;
    padding: 10px 14px;
    color: #e6edf3;
}
#msgAssistant {
    background-color: #161b22;
    border-radius: 12px;
    border-bottom-left-radius: 3px;
    padding: 10px 14px;
    color: #e6edf3;
    border: 1px solid #21262d;
}
#msgRole {
    color: #58a6ff;
    font-size: 12px;
    font-weight: bold;
}
#msgTime {
    color: #484f58;
    font-size: 11px;
}
#refBadge {
    background-color: #1c2d3d;
    border: 1px solid #1f6feb;
    border-radius: 4px;
    color: #58a6ff;
    font-size: 11px;
    padding: 2px 6px;
}
"""
