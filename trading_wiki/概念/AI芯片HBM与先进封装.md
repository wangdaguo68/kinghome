---
title: "AI芯片HBM与先进封装"
type: concept
folder: 概念
created: 2026-06-13
updated: 2026-06-15
status: active
evidence_level: medium
execution_permission: observe_only
source_links:
  - "[[AI全产业链地图]]"
tags:
  - trading/wiki/concept
  - trading/ai-chip
  - trading/hbm
  - trading/advanced-packaging
---

# AI芯片HBM与先进封装

## 概念定义

AI芯片HBM与先进封装，是指 GPU/ASIC、HBM高带宽内存、CoWoS/2.5D/3D封装、ABF载板、硅中介层、底填、塑封料、临时键合、测试和封装设备共同组成的 AI算力核心硬件瓶颈。

这个页面解决的问题：AI芯片不是单独一颗GPU，真正的供给瓶颈经常来自 HBM、先进封装产能、ABF载板和封装材料。

## 产业链结构

| 环节 | 海外核心企业 | 国内/大中华核心企业 | 关键变量 |
| --- | --- | --- | --- |
| GPU/AI加速器 | NVIDIA、AMD、Intel | 华为昇腾、寒武纪、海光信息 | 性能、软件生态、可获得产能 |
| ASIC/定制芯片 | Broadcom、Marvell、Google TPU、AWS Trainium、Microsoft Maia | 百度昆仑芯、壁仞、燧原、芯原股份 | 定制订单、代工、封装 |
| HBM | SK hynix、Samsung、Micron | 长鑫存储、澜起科技等接口/配套方向 | HBM3E/HBM4代际、产能、良率 |
| 晶圆代工 | TSMC、Samsung、Intel Foundry | 中芯国际、华虹公司 | 先进制程、良率、排产 |
| 先进封装 | TSMC CoWoS、ASE、Amkor、Intel、Samsung、BESI、ASMPT | 长电科技、通富微电、华天科技、甬矽电子 | 2.5D/3D能力、产能、客户 |
| 载板 | Ibiden、Shinko、Unimicron、AT&S | 深南电路、兴森科技、珠海越亚等 | ABF/BT载板规格和认证 |
| 封装材料 | Ajinomoto、Resonac、NAMICS、Sumitomo Bakelite | 华海诚科、德邦科技、飞凯材料、雅克科技 | ABF、底填、EMC、临时键合材料 |
| 测试设备 | Teradyne、Advantest | 长川科技、精测电子、华峰测控 | HBM/SoC测试能力 |

## 关键事实与催化

| 线索 | 当前处理 | 事实强度 | L4权限 |
| --- | --- | --- | --- |
| AI加速器需求持续推升HBM需求 | 行业趋势 | 中高 | 需看内存厂出货和价格 |
| CoWoS/2.5D封装是高端AI芯片产能瓶颈之一 | 产业瓶颈 | 中高 | 需看TSMC/OSAT扩产 |
| ABF载板和底填/塑封料是封装材料弹性方向 | 材料线索 | 中 | 需客户认证和订单 |
| 国内公司多为配套和国产替代映射 | 观察假设 | 中低 | 需公告/收入验证 |

## 国内外核心企业

| 位置 | 海外锚 | 国内锚 | 验证重点 |
| --- | --- | --- | --- |
| 算力芯片 | NVIDIA、AMD、Broadcom、Marvell | 寒武纪、海光信息、华为昇腾生态 | 芯片出货、生态、客户 |
| HBM | SK hynix、Samsung、Micron | 长鑫存储、澜起科技 | HBM代际、接口芯片和客户 |
| CoWoS/先进封装 | TSMC、ASE、Amkor | 长电科技、通富微电、华天科技 | 是否承接2.5D/高端封装 |
| ABF/载板 | Ajinomoto、Ibiden、Shinko、Unimicron | 深南电路、兴森科技 | 高端载板规格和认证 |
| 封装材料 | NAMICS、Resonac、Sumitomo、DuPont | 华海诚科、德邦科技、飞凯材料 | 底填/EMC/临时键合订单 |

## 交易验证清单

- [ ] HBM价格、出货和客户分配是否继续偏紧。
- [ ] CoWoS/2.5D封装产能扩张是否跟上GPU需求。
- [ ] ABF载板和封装材料是否进入AI芯片供应链。
- [ ] 国内标的是否有明确客户、订单和收入占比。
- [ ] 先进封装扩产是否已经反映在估值里。

## 资料与证据

| 来源 | 可用信息 | 使用方式 |
| --- | --- | --- |
| [TSMC CoWoS官方资料](https://3dfabric.tsmc.com/english/dedicatedFoundry/technology/cowos.htm) | CoWoS/3DFabric技术路线 | 先进封装背景 |
| [Micron HBM官方资料](https://www.micron.com/products/memory/hbm) | HBM用于AI和高性能计算 | HBM背景 |
| [SK hynix HBM产品资料](https://www.skhynix.com/products.do?ct1=50&ct2=52&lang=eng) | HBM产品线 | HBM背景 |
| [Ajinomoto ABF资料](https://www.ajinomoto.com/innovation/keyword/abf) | ABF作为高端封装载板材料 | 材料背景 |
| [AMD Instinct资料](https://www.amd.com/en/products/accelerators/instinct.html) | AI加速器竞争格局 | 芯片背景 |

## 2026-06-15 认知更新：ABF与硅电容下钻

今天把两个先进封装相关细分页补齐：

| 新页面 | 对本页的补充 | 验证边界 |
| --- | --- | --- |
| [[ABF增层膜与高端载板]] | GPU/ASIC/HBM封装需要高端封装基板，ABF是关键材料之一 | 区分ABF膜、ABF载板和普通PCB |
| [[硅电容与先进封装去耦]] | 高功耗芯片对封装内去耦和电源完整性要求提高 | 区分硅电容/IPD和普通MLCC |

## 结论

AI芯片链的交易价值不能只看GPU品牌，还要看HBM、CoWoS/2.5D、ABF载板和封装材料。国内映射大多处在“国产替代和配套验证”阶段，不能把海外瓶颈直接等同于A股利润。
