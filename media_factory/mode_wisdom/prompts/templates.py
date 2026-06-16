WISDOM_XHS_TEMPLATE = """\
围绕以下主题生成小红书文案。

今日主题：{theme}
经典原文：{primary_text}
出处：{source_metadata}
解读方向：{approach}
语气：{tone}

用户可能关注的痛点：{user_context}

严格规则：
- 标题必须含"停止内耗"或"释怀"或"我终于懂了"等情绪钩子
- 开头必须引用经典原文并标注出处
- 给出1个具体的可执行的心灵练习
- 禁止任何市场/交易/股票词汇
- 禁止空洞的正能量
- Emoji：🌸🧘🌿🕯️💛✨
- 全文800-1500字

生成小红书文案："""

WISDOM_WECHAT_TEMPLATE = """\
围绕以下主题生成公众号深度长文。

今日主题：{theme}
经典原文：{primary_text}
出处：{source_metadata}
解读方向：{approach}
语气：{tone}

备用引用素材：
{additional_quotes}

严格规则：
- 按固定模块结构输出
- 引用必须标注出处
- 每段解读有逻辑推演
- 禁止任何市场/交易/股票词汇
- 拒绝鸡汤，追求思辨深度
- 2000-3500字，比原长文压缩约30%，避免重复铺陈

生成公众号文章："""

WISDOM_WEIBO_TEMPLATE = """\
围绕以下主题生成一条微博（不超过280字）。

今日主题：{theme}
经典原文：{primary_text}
出处：{source_metadata}

严格规则：
- 不超过280字
- 开头引用经典原文
- 一句深度解读
- 带话题标签 #每日智慧# #深度思考#
- 禁止任何市场/交易词汇

生成微博："""

WISDOM_SHIPINHAO_TEMPLATE = """\
围绕以下主题生成短视频口播脚本。

今日主题：{theme}
经典原文：{primary_text}
出处：{source_metadata}

严格规则：
- 「今日智慧」金句不超过30字
- 正文不超过200字
- 开头引用经典
- 禁止任何市场/交易词汇
- 结尾反思问题

生成短视频脚本："""
