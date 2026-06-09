# TDX MCP

通达信行情 MCP 服务。服务同时提供 MCP Streamable HTTP 和少量 REST 调试接口。

## 环境变量

- `TDX_TOKEN`：通达信词元 token，仅保存在服务器 `.env`，不提交。
- `TDX_MCP_ACCESS_TOKEN`：访问本 MCP 服务的密钥。
- `TDX_MCP_HOST`：默认 `0.0.0.0`。
- `TDX_MCP_PORT`：默认 `19110`。

## 接口

- MCP：`/mcp`
- REST 健康检查：`/health`
- REST 行情：`/quotes?codes=000001,600000&access_token=...`
- REST K 线：`/kline/000001?period=day&count=20&access_token=...`
- REST 搜索：`/lookup?keyword=茅台&access_token=...`

访问控制支持三种方式：

- `Authorization: Bearer <TDX_MCP_ACCESS_TOKEN>`
- `X-TDX-MCP-Token: <TDX_MCP_ACCESS_TOKEN>`
- URL 参数 `access_token=<TDX_MCP_ACCESS_TOKEN>`
