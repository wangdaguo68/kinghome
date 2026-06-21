# KingModel 交易决策站点实施计划

日期：2026-06-21
依据：`docs/superpowers/specs/2026-06-21-trading-decision-dashboard-design.md`

## 阶段 1：工程骨架与本地运行

1. 创建 `backend/` FastAPI 工程、依赖和配置加载。
2. 创建 `frontend/` React、TypeScript、Vite 工程。
3. 创建 Dockerfile、Nginx 配置和 Docker Compose。
4. 增加 `.env.example`，确保敏感信息不进入 Git。
5. 验证前后端开发服务器和容器构建。

## 阶段 2：认证与持久化

1. 在 `backend/app/db.py` 建立 SQLite WAL 连接和初始化流程。
2. 在 `backend/app/models.py` 定义用户、采集运行、市场快照、决策快照和舆情实体。
3. 在 `backend/app/auth.py` 实现 Argon2 密码哈希、登录限速和会话认证。
4. 在 `backend/app/api/auth.py` 提供登录、退出和当前用户接口。
5. 为认证和数据库恢复编写测试。

## 阶段 3：通达信 MCP 接入

1. 在 `backend/app/services/tdx_mcp.py` 实现 MCP 初始化、会话续期、工具调用、限速和响应校验。
2. 实现空响应、超时、会话失效和编码异常处理。
3. 增加可复现的 MCP 响应 fixture，测试时不依赖外部服务。
4. 提供 MCP 健康检查和最近成功调用状态。

## 阶段 4：指标与决策引擎

1. 在 `backend/app/engine/universe.py` 实现交易池过滤。
2. 在 `backend/app/engine/market.py` 计算赚钱、亏钱、趋势和投机规则分。
3. 在 `backend/app/engine/cycle.py` 实现周期状态机。
4. 在 `backend/app/engine/sectors.py` 实现板块迁移和主线评分。
5. 在 `backend/app/engine/cores.py` 实现三类核心评分。
6. 在 `backend/app/engine/decision.py` 执行硬门槛并生成许可、仓位、触发和失效条件。
7. 为每个引擎模块编写单元测试，覆盖正常、边界和缺失数据。

## 阶段 5：采集、快照与 API

1. 在 `backend/app/services/collector.py` 按快、中、慢三档组织 MCP 查询。
2. 在 `backend/app/services/scheduler.py` 配置盘中、盘后和隔夜任务。
3. 实现最近成功值、数据新鲜度、部分更新和正式收盘快照。
4. 提供驾驶舱、市场图谱、板块、核心、复盘、历史、舆情和设置 API。
5. 提供 WebSocket 推送和断线重连所需版本号。

## 阶段 6：决策驾驶舱前端

1. 建立登录页、认证状态和受保护路由。
2. 实现决策驾驶舱首屏，保持许可、主线、核心和风险无需滚动可见。
3. 实现市场资金迁移图谱、板块详情和核心详情。
4. 实现隔夜舆情、盘后复盘、历史验证和系统设置页面。
5. 实现新鲜度、降级、加载、空数据和错误状态。
6. 实现电脑大屏优先和手机只读适配。
7. 验证键盘可用性、对比度和减少动态效果设置。

## 阶段 7：舆情第一阶段

1. 接入通达信可用舆情和交易所公开公告。
2. 为东方财富公开内容预留稳定连接器；无法稳定访问时明确显示未接入。
3. 实现 URL/标题/事件去重、来源分级和板块映射。
4. 输出催化、共识、拥挤、信息增量和次日验证条件。
5. 确认舆情不直接修改市场评分和仓位。

## 阶段 8：质量验证

1. 运行 Python 单元和集成测试。
2. 运行 TypeScript 检查、前端测试和生产构建。
3. 运行 Docker Compose 构建和健康检查。
4. 使用本地浏览器验证登录、驾驶舱、刷新、展开解释和移动端布局。
5. 检查 Git 差异、敏感信息、占位符和无关文件。

## 阶段 9：阿里云部署

1. 只读检查服务器系统、Docker、端口、磁盘、现有服务和 MCP 配置。
2. 创建独立部署目录和服务器环境文件，不覆盖无关服务。
3. 构建并启动容器，Nginx 发布 19098，API 仅内部访问。
4. 创建初始站点用户并只在交付信息中提供一次临时密码。
5. 验证公网登录、API 权限、MCP 健康、实时刷新和持久化。
6. 验证容器重启恢复和回滚命令。

## 阶段 10：提交与交付

1. 提交实现代码和测试。
2. 推送 `codex/trading-mode-framework`。
3. 交付访问地址、登录信息、运行状态、已接入数据、限制和后续 HTTPS 升级建议。
