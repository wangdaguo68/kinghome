from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"


@dataclass(frozen=True)
class FeishuConfig:
    app_id: str
    app_secret: str
    chat_id: str
    enabled: bool

    @property
    def configured(self) -> bool:
        return bool(self.app_id and self.app_secret and self.chat_id)


class FeishuNotifier:
    def __init__(self, config: FeishuConfig | None = None) -> None:
        self.config = config or feishu_config()
        self._token: str | None = None
        self._token_expires_at = 0.0

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.config.enabled,
            "configured": self.config.configured,
            "chat_id": mask_id(self.config.chat_id),
            "mode": "飞书群消息",
        }

    def send_text(self, text: str) -> dict[str, object]:
        if not self.config.enabled:
            return {"sent": False, "reason": "FEISHU_ENABLED 未开启"}
        if not self.config.configured:
            return {"sent": False, "reason": "飞书 AppID/AppSecret/ChatID 未配置完整"}

        token = self._tenant_access_token()
        payload = {
            "receive_id": self.config.chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        response = _post_json(MESSAGE_URL, payload, headers={"Authorization": f"Bearer {token}"})
        if response.get("code") != 0:
            return {"sent": False, "reason": response.get("msg", "飞书接口返回异常"), "response": response}
        return {"sent": True, "message_id": response.get("data", {}).get("message_id")}

    def _tenant_access_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expires_at - 60:
            return self._token

        payload = {"app_id": self.config.app_id, "app_secret": self.config.app_secret}
        response = _post_json(TOKEN_URL, payload)
        token = response.get("tenant_access_token")
        if response.get("code") != 0 or not token:
            raise RuntimeError(response.get("msg", "获取飞书 tenant_access_token 失败"))
        self._token = str(token)
        self._token_expires_at = now + float(response.get("expire", 7200))
        return self._token


def feishu_config() -> FeishuConfig:
    return FeishuConfig(
        app_id=os.getenv("FEISHU_APP_ID", ""),
        app_secret=os.getenv("FEISHU_APP_SECRET", ""),
        chat_id=os.getenv("FEISHU_CHAT_ID", ""),
        enabled=os.getenv("FEISHU_ENABLED", "0") == "1",
    )


def mask_id(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return value[:2] + "***"
    return value[:6] + "***" + value[-4:]


def _post_json(url: str, payload: dict[str, object], headers: dict[str, str] | None = None) -> dict[str, object]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            **(headers or {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"飞书接口连接失败: {exc}") from exc
