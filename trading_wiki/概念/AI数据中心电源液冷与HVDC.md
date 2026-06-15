---
title: "AI数据中心电源液冷与HVDC"
type: concept
folder: 概念
created: 2026-06-13
updated: 2026-06-15
status: active
evidence_level: medium
execution_permission: observe_only
source_links:
  - "[[AI全产业链地图]]"
  - "[[有色金属AI电力需求链]]"
tags:
  - trading/wiki/concept
  - trading/data-center
  - trading/liquid-cooling
  - trading/power
---

# AI数据中心电源液冷与HVDC

## 概念定义

AI数据中心电源液冷与HVDC，指 AI服务器功率密度上升后，数据中心从传统风冷、低功率机柜向高功率机柜、液冷、UPS/HVDC、配电、变压器、母线、储能和能源管理升级的产业链。

AI算力的约束不只在GPU，也在电力接入、机柜功率、散热效率和交付周期。

## 产业链结构

| 环节 | 设备/能力 | 海外核心企业 | 国内/大中华核心企业 | 验证重点 |
| --- | --- | --- | --- | --- |
| 供配电 | 变压器、开关柜、母线、配电柜 | Schneider、Eaton、ABB、Siemens | 特变电工、许继电气、平高电气、良信股份 | 数据中心项目和订单 |
| UPS/HVDC | UPS、HVDC、整流、电源模块 | Vertiv、Schneider、Eaton、Delta | 科华数据、科士达、中恒电气、麦格米特、台达电 | 高功率机柜配套 |
| 液冷 | 冷板、CDU、泵、管路、快接头 | Vertiv、CoolIT、Asetek、Schneider | 英维克、申菱环境、高澜股份、依米康、同飞股份 | 液冷订单、客户和交付 |
| 温控工程 | 精密空调、冷机、机房工程 | Johnson Controls、Trane、Carrier | 英维克、申菱环境、佳力图 | PUE、项目毛利率 |
| 电力资源 | 电网、绿电、储能 | NextEra、Enel、Tesla Energy | 三峡能源、阳光电源、宁德时代、南网科技 | 电力接入和储能配套 |
| 原料 | 铜、铝、钢、制冷剂、功率半导体 | Freeport、Alcoa、Infineon、onsemi | 紫金矿业、中国铝业、北方华创、斯达半导 | 成本和供给 |

## 关键事实与催化

| 线索 | 当前处理 | 事实强度 | L4权限 |
| --- | --- | --- | --- |
| AI服务器单柜功率上升推动液冷渗透 | 行业趋势 | 中 | 需订单验证 |
| GB200/Blackwell等平台提升电源散热要求 | 产业背景 | 中 | 需客户项目 |
| HVDC、UPS、电源模块可能受益 | 设备线索 | 中低 | 需收入占比 |
| 铜铝等原料需求上升 | 原料链观察 | 中低 | 需商品和库存数据 |

## 核心受益标的

| 标的 | 位置 | 正面逻辑 | 需要验证 |
| --- | --- | --- | --- |
| Vertiv | 全球数据中心电源和热管理 | AI数据中心基础设施龙头 | 订单和毛利率 |
| Schneider Electric | 配电和能源管理 | 数据中心电气系统 | 数据中心业务增速 |
| Delta/台达电 | 电源和散热 | AI服务器电源与散热配套 | 高功率电源订单 |
| 英维克 | 温控/液冷 | 国内液冷和机房温控标的 | 客户、订单、交付 |
| 申菱环境 | 温控和液冷 | 数据中心温控和液冷映射 | 液冷收入占比 |
| 高澜股份 | 液冷设备 | 冷却系统方向 | AI数据中心客户 |
| 科华数据 | UPS/数据中心 | 电源和IDC | AI机房订单 |
| 麦格米特 | 电源模块 | AI电源和工业电源映射 | 服务器电源客户 |

## 验证清单

- [ ] 单柜功率和液冷方案是否来自正式项目。
- [ ] 是冷板式、浸没式还是机房级温控，价值量不同。
- [ ] 设备订单是否能确认收入，毛利率是否被工程属性稀释。
- [ ] 电源/HVDC是否进入AI服务器或数据中心项目，而不是传统电源。
- [ ] 铜铝等原料上涨是需求弹性还是成本压力。

## 资料与证据

| 来源 | 可用信息 | 使用方式 |
| --- | --- | --- |
| [Vertiv AI Hub](https://www.vertiv.com/en-us/solutions/ai-hub/) | AI数据中心电源和冷却需求 | 行业背景 |
| [Schneider Electric AI数据中心资料](https://www.se.com/us/en/work/solutions/for-business/data-centers-and-networks/artificial-intelligence/) | AI数据中心电力与冷却方案 | 行业背景 |
| [NVIDIA GB200 NVL72资料](https://www.nvidia.com/en-us/data-center/gb200-nvl72/) | 高功率AI服务器平台 | 需求背景 |
| [Delta数据中心解决方案](https://www.deltaww.com/en-US/solutions/Data-Center-Solutions/ALL/) | 电源、热管理、数据中心解决方案 | 企业背景 |

## 2026-06-15 认知更新：冷媒与液冷材料拆分

今日新增[[制冷剂与氟化液冷]]。AI数据中心液冷链条需要分三层：

| 层级 | 代表内容 | 验证重点 |
| --- | --- | --- |
| 液冷系统 | 冷板、CDU、泵阀、管路、机柜集成 | 数据中心订单和交付 |
| 冷却液/氟化液 | 浸没式或特定液冷冷媒 | 牌号、绝缘性、环保和客户验证 |
| 普通制冷剂 | R32/R125/R134a等 | 配额、价格、空调/汽车需求 |

不能把普通制冷剂涨价直接等同于AI液冷订单。

## 结论

电源液冷链是 AI算力从芯片走向数据中心交付的关键约束。真正有价值的跟踪不是“液冷概念”，而是高功率机柜订单、客户项目、交付周期、毛利率和原料成本。
