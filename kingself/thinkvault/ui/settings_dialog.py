"""设置对话框：AI 模型 + 嵌入向量配置。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QTextEdit, QTabWidget, QWidget, QCheckBox,
    QMessageBox, QFrame,
)

import core.database as db


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(580, 520)
        self._cfg = db.get_settings()
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_ai_tab(), "AI 模型")
        tabs.addTab(self._build_embedding_tab(), "向量嵌入")
        tabs.addTab(self._build_general_tab(), "通用")
        layout.addWidget(tabs, 1)

        # 底部按钮
        btns = QHBoxLayout()
        btns.addStretch()
        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save)
        btns.addWidget(save_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

    # ── AI 标签页 ──────────────────────────────────────────────────────────────

    def _build_ai_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.ai_provider_box = QComboBox()
        self.ai_provider_box.addItems(["openai", "deepseek", "anthropic", "ollama", "custom"])
        self.ai_provider_box.currentTextChanged.connect(self._on_provider_change)
        form.addRow("服务商：", self.ai_provider_box)

        self.ai_base_url = QLineEdit()
        self.ai_base_url.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("Base URL：", self.ai_base_url)

        self.ai_api_key = QLineEdit()
        self.ai_api_key.setEchoMode(QLineEdit.Password)
        self.ai_api_key.setPlaceholderText("sk-…")
        form.addRow("API Key：", self.ai_api_key)

        self.ai_model = QLineEdit()
        self.ai_model.setPlaceholderText("gpt-4o-mini")
        form.addRow("模型名称：", self.ai_model)

        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_ai)
        form.addRow("", test_btn)

        form.addRow(self._sep())

        self.system_prompt = QTextEdit()
        self.system_prompt.setMaximumHeight(100)
        self.system_prompt.setPlaceholderText("System Prompt…")
        form.addRow("系统提示词：", self.system_prompt)

        self.stream_check = QCheckBox("启用流式输出")
        form.addRow("", self.stream_check)

        return w

    # ── 嵌入标签页 ────────────────────────────────────────────────────────────

    def _build_embedding_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        hint = QLabel(
            "本地模式：使用 ONNX MiniLM 模型（首次运行自动下载，约 23 MB，无需 API Key）\n"
            "API 模式：使用 OpenAI 兼容接口（需配置 Key 和 URL）"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#8b949e; font-size:12px;")
        form.addRow(hint)
        form.addRow(self._sep())

        self.embed_provider_box = QComboBox()
        self.embed_provider_box.addItems(["local", "api"])
        self.embed_provider_box.currentTextChanged.connect(self._on_embed_provider_change)
        form.addRow("嵌入来源：", self.embed_provider_box)

        self.embed_base_url = QLineEdit()
        self.embed_base_url.setPlaceholderText("https://api.openai.com/v1")
        form.addRow("Base URL：", self.embed_base_url)

        self.embed_api_key = QLineEdit()
        self.embed_api_key.setEchoMode(QLineEdit.Password)
        self.embed_api_key.setPlaceholderText("sk-…")
        form.addRow("API Key：", self.embed_api_key)

        self.embed_model = QLineEdit()
        self.embed_model.setPlaceholderText("text-embedding-3-small")
        form.addRow("模型名称：", self.embed_model)

        reload_btn = QPushButton("重载嵌入配置")
        reload_btn.clicked.connect(self._reload_embed)
        form.addRow("", reload_btn)

        return w

    # ── 通用标签页 ────────────────────────────────────────────────────────────

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.rag_check = QCheckBox("启用 RAG（对话时自动引用相关历史记忆）")
        form.addRow("", self.rag_check)

        self.rag_topk = QComboBox()
        for n in [1, 2, 3, 5, 8, 10, 15, 20]:
            self.rag_topk.addItem(f"{n} 条", n)
        form.addRow("引用记忆数量：", self.rag_topk)

        form.addRow(self._sep())

        data_lbl = QLabel(f"数据存储路径：{db.DATA_DIR}")
        data_lbl.setStyleSheet("color:#8b949e; font-size:12px;")
        data_lbl.setWordWrap(True)
        form.addRow(data_lbl)

        return w

    # ── 工具方法 ──────────────────────────────────────────────────────────────

    def _sep(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("background:#30363d; border:none; max-height:1px;")
        return f

    def _on_provider_change(self, provider: str):
        presets = {
            "openai":    ("https://api.openai.com/v1",      "gpt-4o-mini"),
            "deepseek":  ("https://api.deepseek.com",        "deepseek-chat"),
            "anthropic": ("https://api.anthropic.com/v1",   "claude-3-5-haiku-20241022"),
            "ollama":    ("http://localhost:11434/v1",       "llama3.2"),
            "custom":    ("",                               ""),
        }
        url, model = presets.get(provider, ("", ""))
        if url:
            self.ai_base_url.setText(url)
        if model:
            self.ai_model.setText(model)

    def _on_embed_provider_change(self, provider: str):
        api_mode = provider == "api"
        self.embed_base_url.setEnabled(api_mode)
        self.embed_api_key.setEnabled(api_mode)
        self.embed_model.setEnabled(api_mode)

    def _load(self):
        c = self._cfg
        self.ai_provider_box.setCurrentText(c.get("ai_provider", "openai"))
        self.ai_base_url.setText(c.get("ai_base_url", ""))
        self.ai_api_key.setText(c.get("ai_api_key", ""))
        self.ai_model.setText(c.get("ai_model", ""))
        self.system_prompt.setPlainText(c.get("ai_system_prompt", ""))
        self.stream_check.setChecked(c.get("stream_enabled", "true") == "true")

        self.embed_provider_box.setCurrentText(c.get("embedding_provider", "local"))
        self.embed_base_url.setText(c.get("embedding_base_url", ""))
        self.embed_api_key.setText(c.get("embedding_api_key", ""))
        self.embed_model.setText(c.get("embedding_model", ""))
        self._on_embed_provider_change(self.embed_provider_box.currentText())

        self.rag_check.setChecked(c.get("rag_enabled", "true") == "true")
        target_k = int(c.get("rag_top_k", "10"))
        for i in range(self.rag_topk.count()):
            if self.rag_topk.itemData(i) == target_k:
                self.rag_topk.setCurrentIndex(i)
                break

    def _save(self):
        db.set_setting("ai_provider",      self.ai_provider_box.currentText())
        db.set_setting("ai_base_url",      self.ai_base_url.text().strip())
        db.set_setting("ai_api_key",       self.ai_api_key.text().strip())
        db.set_setting("ai_model",         self.ai_model.text().strip())
        db.set_setting("ai_system_prompt", self.system_prompt.toPlainText().strip())
        db.set_setting("stream_enabled",   "true" if self.stream_check.isChecked() else "false")

        db.set_setting("embedding_provider", self.embed_provider_box.currentText())
        db.set_setting("embedding_base_url", self.embed_base_url.text().strip())
        db.set_setting("embedding_api_key",  self.embed_api_key.text().strip())
        db.set_setting("embedding_model",    self.embed_model.text().strip())

        db.set_setting("rag_enabled", "true" if self.rag_check.isChecked() else "false")
        db.set_setting("rag_top_k",   str(self.rag_topk.currentData()))

        # 重置 AI 客户端缓存
        import core.ai_client as ai_c
        ai_c._client = None
        ai_c._last_cfg_hash = ""

        self.accept()

    def _test_ai(self):
        from core.ai_client import test_connection
        base_url = self.ai_base_url.text().strip()
        api_key  = self.ai_api_key.text().strip()
        model    = self.ai_model.text().strip()
        if not base_url or not model:
            QMessageBox.warning(self, "参数缺失", "请先填写 Base URL 和模型名称。")
            return
        try:
            reply = test_connection(base_url, api_key, model)
            QMessageBox.information(self, "连接成功 ✓", f"AI 回复：{reply[:300]}")
        except RuntimeError as e:
            QMessageBox.warning(self, "连接失败", str(e))

    def _reload_embed(self):
        from core.memory import reload_collection
        reload_collection()
        QMessageBox.information(self, "已重载", "嵌入配置已重载，下次存储时生效。")
