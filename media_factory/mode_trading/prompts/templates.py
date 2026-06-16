TRADING_XHS_TEMPLATE = """\
将以下 A 股技术分析数据转化为小红书爆款文案。

今日市场数据：
{market_data}

技术指标汇总：
- MACD: {macd_signal}
- KDJ: {kdj_signal}
- 布林带: {bollinger_signal}
- 均线: {ma_signal}
- 量能: {volume_signal}

关键价位：支撑 {support_levels} / 阻力 {resistance_levels}
市场情绪指标：涨跌比 {breadth}，北向资金 {north_flow}

严格规则：
- 标题必须含具体指标名或数据
- 禁止任何佛学/哲学/心理学词汇
- 禁止心灵鸡汤
- Emoji 只用 📊📈📉💰🔥⚡
- 全文800-1500字

生成小红书文案："""

TRADING_WECHAT_TEMPLATE = """\
将以下 A 股技术分析数据转化为公众号深度复盘文章。

今日市场数据：
{market_data}

技术指标汇总：
- MACD: {macd_signal}
- KDJ: {kdj_signal}
- 布林带: {bollinger_signal}
- 均线: {ma_signal}
- 量能: {volume_signal}

关键价位：支撑 {support_levels} / 阻力 {resistance_levels}
市场情绪指标：涨跌比 {breadth}，北向资金 {north_flow}

严格规则：
- 按固定模块结构输出
- 所有数据精确到具体数字
- 禁止任何佛学/禅修/心灵相关词汇
- 纯技术分析视角
- 2000-3500字，比原长文压缩约30%，避免重复铺陈

生成公众号文章："""

TRADING_WEIBO_TEMPLATE = """\
将以下 A 股技术信号转化为一条微博（不超过280字）。

今日最核心信号：{key_signal}
市场数据摘要：{market_summary}

严格规则：
- 不超过280字
- 开头金句直击要害
- 带话题标签 #A股复盘# #技术分析#
- 禁止任何佛学/鸡汤

生成微博："""

TRADING_SHIPINHAO_TEMPLATE = """\
将以下 A 股技术信号转化为短视频口播脚本。

今日最核心信号：{key_signal}
市场数据摘要：{market_summary}

严格规则：
- 「今日信号」金句不超过30字
- 正文不超过200字
- 只说技术信号，不灌鸡汤
- 结尾行动问题

生成短视频脚本："""
