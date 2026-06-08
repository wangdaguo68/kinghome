# 产业研报模块设计

## 目标

新增“产业研报”页面，用于沉淀卖方研报、产业报告、电话会议纪要、买方模型拆解等研究材料的元数据与摘要。系统只采集合规来源：公开网页/API、用户已授权来源、或用户提供的本地文件，不绕过登录、付费墙或权限校验。

## 数据模型

使用 MySQL 入库，新增三张表：

- `industry_research_sources`：记录来源名称、来源类型、URL、启用状态、最近同步时间和错误信息。
- `industry_research_items`：记录标题、摘要、类型、来源、机构、作者、行业、关联股票、标签、发布时间、抓取时间、内容哈希和原始载荷。
- `industry_research_crawl_runs`：记录每次同步的状态、成功条数、失败条数和错误信息。

`industry_research_items.content_hash` 做唯一键，保证重复同步不会重复入库。

## 后端接口

- `GET /api/industry-research`：分页查询，支持类型、来源、行业、股票、关键词筛选。
- `GET /api/industry-research/stats`：返回总条数、今日新增、来源数、最近更新时间。
- `GET /api/industry-research/sources`：返回来源同步状态。
- `GET /api/industry-research/sync`：手动触发同步。

## 采集策略

第一期内置东方财富研报中心公开列表接口，覆盖个股研报、行业研报、宏观/策略类公开研报元数据；同时支持：

- `INDUSTRY_RESEARCH_SOURCES_JSON` 配置自定义公开 JSON/RSS/HTML 来源。
- `INDUSTRY_RESEARCH_IMPORT_DIR` 配置本地文件导入目录，支持 `.md`、`.txt`、`.json`。

后台线程每天固定时间同步，环境变量控制开关和时间。

## 前端

新增左侧菜单“产业研报”。页面采用研究信息流布局：顶部统计、筛选区、列表卡片、分页器。每条记录展示来源、来源类型、发布时间、机构、行业、作者、关联股票和摘要。

## 风险处理

数据库不可用时接口返回空结果和提示，不阻塞其它页面。爬虫失败会写入 crawl run 和 source error。页面加载只读数据库，不实时爬取，避免拖慢主系统。
