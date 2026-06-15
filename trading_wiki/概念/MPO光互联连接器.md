---
title: "MPO光互联连接器"
type: concept
folder: 概念
domain: 产业系统
system: 产业系统
systems:
  - 产业系统
  - 智能系统
  - 物理系统
created: 2026-06-15
updated: 2026-06-15
status: active
evidence_level: medium
execution_permission: observe_only
topics:
  - MPO
  - MTP
  - 光互联
  - AI数据中心
  - CPO
aliases:
  - MPO插芯
  - MPO连接器
  - MTP连接器
tags:
  - trading/wiki/concept
  - trading/ai-hardware
  - trading/optical-interconnect
source_links:
  - "[[CPO与1.6T硅光光模块]]"
  - "[[AI全产业链地图]]"
---

# MPO光互联连接器

## 概念定义

MPO是Multi-fiber Push On，多芯光纤推拉式连接器；MTP通常可理解为高性能MPO连接器体系。它的作用不是“发光”或“做光模块”，而是在AI数据中心高密度光纤布线中，把多芯光纤以更小空间、更高密度、更少插拔次数接入交换机、光模块、配线架和机柜。

在AI训练集群里，GPU服务器之间需要大量高速互联。800G、1.6T、CPO/NPO和机柜级光互联提升后，单个数据中心的光纤端口密度、布线复杂度和可靠性要求上升，MPO连接器、MT插芯、跳线和配线系统因此获得关注。

本概念不是[[CPO与1.6T硅光光模块]]的替代，而是它的连接和布线层。

## 产业链结构

| 环节 | 作用 | 关键能力 | 海外核心企业 | 国内核心企业线索 |
| --- | --- | --- | --- | --- |
| 光纤预制棒/光纤 | 光信号传输介质 | 低损耗、稳定性、规模制造 | Corning、Prysmian、OFS、Fujikura | 长飞光纤、亨通光电、中天科技、烽火通信 |
| MT插芯 | 多芯光纤精密定位 | 微米级孔位精度、端面加工、良率 | US Conec、Senko、Fujikura | 太辰光、长芯博创等需验证 |
| MPO/MTP连接器 | 高密度多芯连接 | 低插损、低回损、重复插拔可靠性 | US Conec、Senko、Molex、TE Connectivity、Amphenol | 太辰光、博创科技、光迅科技、长飞光纤等需验证 |
| 跳线/预端接线缆 | 机柜与交换机连接 | 工程交付、定制化、测试能力 | Corning、CommScope、Leviton | 亨通光电、中天科技、长飞光纤 |
| 光模块/交换机 | 形成高速端口需求 | 800G/1.6T、OSFP/QSFP、CPO/NPO | Broadcom、NVIDIA、Arista、Coherent | 中际旭创、新易盛、天孚通信、光迅科技 |

## 核心受益标的

只列与MPO、光纤连接、光器件更直接相关的环节；普通光模块、交换机、数据中心工程不作为本页核心。

| 标的/公司线索 | 位置 | 正面逻辑 | 需要验证 |
| --- | --- | --- | --- |
| 太辰光 | 光器件、光连接器、陶瓷/MT插芯线索 | 若MPO/MT插芯进入AI数据中心客户，价值量和弹性更直接 | 产品占比、客户、800G/1.6T相关订单 |
| 博创科技 | 光器件、光模块相关 | 可能受益于数据中心光互联需求 | MPO具体产品、客户认证和订单 |
| 光迅科技 | 光器件和模块平台 | 光通信全栈能力强 | MPO连接器/插芯是否为主要收入 |
| 长飞光纤 | 光纤光缆和数据中心连接 | 上游光纤与高密度布线需求 | AI数据中心项目、产品结构 |
| 亨通光电/中天科技 | 光纤光缆和通信网络 | 光纤基础设施需求 | 数据中心高端连接产品占比 |

## 关键事实与催化

| 线索 | 当前处理 | 事实强度 | L4权限 |
| --- | --- | --- | --- |
| AI集群互联提高光纤端口密度 | 作为长期趋势 | 中高 | 需看云厂商和交换机架构 |
| 800G/1.6T与CPO/NPO提高连接复杂度 | 作为上游传导 | 中 | 需看MPO规格和BOM |
| MPO插芯成为今日舆情热点 | 作为观察假设 | 中低 | 需看具体公司订单 |
| “做光通信”不等于“做MPO插芯” | 作为反证规则 | 高 | 必须逐家公司验证 |

## 和相关页面的区别

- [[CPO与1.6T硅光光模块]]：关注光模块、硅光、交换机和CPO架构；本页关注连接器、插芯、跳线和配线。
- [[AI服务器PCB提价链]]：关注电互联材料；本页关注光互联连接。
- [[AI全产业链地图]]：总图谱；本页是光通信链路下钻。

## 验证清单

- [ ] 公司是否明确披露MPO/MTP、MT插芯、多芯连接器或预端接光缆产品。
- [ ] 是否进入AI数据中心、800G/1.6T、CPO/NPO相关客户。
- [ ] 产品是元件、组件还是工程布线，毛利率和规模不同。
- [ ] 是否有海外大客户认证、批量出货和收入占比。
- [ ] 插损、回损、端面良率、批量一致性是否达到高端要求。

## 引用来源

- [Corning：MTP连接器用于高密度数据中心连接](https://www.corning.com/data-center/worldwide/en/home/knowledge-center/maximizing-the-advantages-of-the-mtp-connector.html)
- [Corning：光纤与生成式AI革命](https://www.corning.com/optical-communications/worldwide/en/home/the-signal-network-blog/optical-fiber-and-the-generative-ai-revolution.html)
- [[sources/2026-06-15]]

## 结论

MPO的交易价值在于“AI数据中心光互联密度提升后的连接层瓶颈”。它不能简单等同于光模块行情，真正的验证点是插芯、连接器和跳线组件是否进入高端AI集群BOM，并形成订单和毛利。

