import asyncio
import json
import time
from typing import Any

import httpx


class TdxMcpError(RuntimeError):
    pass


class TdxMcpClient:
    def __init__(self, url: str, token: str, timeout: float = 35.0) -> None:
        self.url = url
        self.token = token
        self.timeout = timeout
        self.session_id: str | None = None
        self.last_success_at: float | None = None
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.url and self.token)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json, text/event-stream", "Authorization": f"Bearer {self.token}"}
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        return headers

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.post(self.url, headers=self._headers(), json=payload)

    async def initialize(self) -> None:
        response = await self._post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "kingmodel", "version": "1.0"},
                },
            }
        )
        response.raise_for_status()
        self.session_id = response.headers.get("mcp-session-id")
        await self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    @staticmethod
    def _parse_sse(text: str) -> dict[str, Any]:
        for line in text.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
        raise TdxMcpError("MCP response does not contain an SSE data event")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise TdxMcpError("TDX MCP is not configured")
        async with self._lock:
            delay = 0.65 - (time.monotonic() - self._last_call)
            if delay > 0:
                await asyncio.sleep(delay)
            for attempt in range(2):
                if not self.session_id:
                    await self.initialize()
                response = await self._post(
                    {
                        "jsonrpc": "2.0",
                        "id": int(time.time() * 1000) % 2_000_000_000,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": arguments,
                        },
                    }
                )
                self._last_call = time.monotonic()
                if response.status_code == 400 and attempt == 0:
                    self.session_id = None
                    continue
                response.raise_for_status()
                envelope = self._parse_sse(response.text)
                if "error" in envelope:
                    raise TdxMcpError(str(envelope["error"]))
                result = envelope.get("result", {})
                structured = result.get("structuredContent")
                if not isinstance(structured, dict):
                    raise TdxMcpError("MCP response does not contain structuredContent")
                self.last_success_at = time.time()
                return structured
        raise TdxMcpError("TDX MCP session could not be renewed")
