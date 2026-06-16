TECH_ANALYSIS_TEMPLATE = """\
Analyze the following A-share market review. Identify and describe:

1. Key technical patterns (breakouts, divergences, reversals, trend changes)
2. Volume signals (accumulation, distribution, climax, drying up)
3. Market sentiment from the language used
4. Key support and resistance levels with rationale
5. Specific sectors or themes active today

Market Review Text:
{raw_text}

Return your analysis in Chinese, structured clearly with these sections:
## 技术形态
## 量能信号
## 市场情绪
## 关键价位
## 活跃板块"""


PHILOSOPHY_MAPPING_TEMPLATE = """\
Map the following technical analysis to Buddhist philosophy, cognitive psychology, \
and Eastern wisdom. Be specific — every mapping must be anchored to a concrete \
market observation.

Technical Analysis:
{tech_analysis}

Original Market Context:
{market_context}

Requirements:
1. Identify 3-5 Buddhist concepts that apply (无常/因果/空性/贪嗔痴/缘起/无我)
2. For each concept, explain how it manifests in TODAY's specific market action
3. Identify 2-3 cognitive biases likely affecting traders today
4. Extract 2-3 philosophical themes for today's market
5. Craft a one-sentence "key narrative" that ties analysis, philosophy, and psychology together

Return in Chinese, structured as:
## 佛法映射
- 概念：具体盘中对应
## 认知偏差
- 偏差名称：今日盘面中的表现
## 哲学主题
- 主题
## 核心叙事
一句话总结"""


XIAOHONGSHU_USER_TEMPLATE = """\
Transform this enriched market analysis into a Xiaohongshu post.

Today's Market Context:
{market_summary}

Enriched Analysis:
Buddhist Mappings: {buddhist_mappings}
Cognitive Biases: {cognitive_biases}
Core Narrative: {key_narrative}
Market Sentiment: {sentiment}

CRITICAL RULES — you MUST follow:
- Title MUST contain "绝了" or "家人们" (required!)
- EVERY paragraph MUST end with 3-5 emojis (required!)
- Open with "最近有没有这种感觉..." pattern
- Each paragraph is 1-2 sentences only
- Close with a gentle question inviting comments
- Tone: warm big sister sharing secrets about the market
- Total: 800-1500 characters

Generate the Xiaohongshu post now:"""


WECHAT_USER_TEMPLATE = """\
Transform this enriched market analysis into a WeChat Official Account long-form article.

Today's Market Context:
{market_summary}

Technical Patterns: {technical_patterns}

Enriched Analysis:
Buddhist Mappings: {buddhist_mappings}
Cognitive Biases: {cognitive_biases}
Philosophical Themes: {philosophical_themes}
Core Narrative: {key_narrative}

CRITICAL RULES — you MUST follow:
- MUST include the fixed module 「🪷 禅意复盘」as the article's centerpiece
- Use 「」 instead of English quotes throughout
- Use `· ◇ ·` or `— ✧ —` as section dividers
- Each sub-section title should be a Buddhist term (e.g., 「无常观市」「因果不虚」)
- Quote Buddhist scriptures where relevant (《金刚经》《心经》preferred)
- Data must be specific: mention exact index levels, percentages, dates
- Ceremonial, ritualistic formatting throughout
- 2000-3500 Chinese characters total, about 30% shorter than the previous long-form version
- Minimal emoji: only 🪷 as Zen marker

Follow this structure:
1. Hook (1-2 paragraphs, pose today's deep question)
2. 盘面数据回顾 (precise data)
3. 技术解盘 (pattern analysis)
4. · ◇ ·
5. 🪷 禅意复盘
   - 无常观市
   - 因果不虚
   - 诸法无我
6. · ◇ ·
7. 心理陷阱
8. 修行建议
9. 结语 (Zen quote)

Generate the WeChat article now:"""


XUEQIU_USER_TEMPLATE = """\
Transform this enriched market analysis into a Xueqiu/Eastmoney post.

Today's Market Context:
{market_summary}

Technical Patterns: {technical_patterns}

Enriched Analysis:
Buddhist Mappings: {buddhist_mappings}
Cognitive Biases: {cognitive_biases}
Core Narrative: {key_narrative}

CRITICAL RULES — you MUST follow:
- EVERY technical indicator mentioned MUST have a philosophical translation
  Example pattern: "[技术信号]不是[表面含义]，是市场在告诉你——[哲学洞察]"
- Professional but not cold — rational analysis with moments of sudden insight
- Every 2-3 paragraphs, drop one "enlightenment-level" philosophical conclusion
- Data accurate, logic tight, leave reader thinking deeply
- 800-2000 characters
- Moderate emoji use (📊📈🧘⚡🔥) — sparse, only for emphasis

Structure:
1. 今日盘面 (3-5 bullet facts, concise)
2. 技术视角 (1-2 patterns deep dive)
3. 哲学转译 (tech → philosophy mapping — this is the CORE value)
4. 仓位禅意 (position management advice infused with Buddhist practice)
5. 互动 (one deep question for reader reflection)

Generate the Xueqiu post now:"""


SHIPINHAO_USER_TEMPLATE = """\
Transform this enriched market analysis into a Video Account/Douyin short post.

Today's Market Context:
{market_summary}

Core Narrative: {key_narrative}
Market Sentiment: {sentiment}

CRITICAL RULES — you MUST follow:
- Generate ONE 「每日禅语」golden quote: max 30 Chinese characters, suitable as 16:9 video background text overlay
- Body: max 200 characters total, max 5 short paragraphs
- Every sentence max 30 characters
- Cut filler words: remove unnecessary "的""了""是"
- Open by hitting pain directly: "割肉那一刻..." "追高的瞬间..." "踏空的感觉..."
- Buddhist insight must land like a slap AND a hug simultaneously
- End with a lingering question
- Only 2-3 emojis total, punchline emphasis only

Output format:
【每日禅语】
<golden quote here, marked clearly>

<body text>

<hook question>

Generate the Video Account post now:"""


WEIBO_USER_TEMPLATE = """\
Transform this enriched market analysis into a Weibo post.

Today's Market Context:
{market_summary}

Core Narrative: {key_narrative}
Market Sentiment: {sentiment}

CRITICAL RULES:
- Max 280 characters total
- Opening: one sharp punchline that hits pain directly
- 1-2 Buddhist/psychology insight lines
- MUST include hashtags: #禅意交易# #A股修行#
- 2-3 emojis only for emphasis

Generate the Weibo post now:"""


VISUAL_PROMPT_TEMPLATE = """\
Based on the following market analysis, generate a cover image prompt for AI art generation.

Market Sentiment: {sentiment}
Key Narrative: {key_narrative}
Philosophical Themes: {philosophical_themes}

Style Preferences:
- Default style: {default_style}
- Aspect ratio: {aspect_ratio}

Guidelines:
- Bullish/optimistic → sunrise, mountain peaks, blooming lotus, golden light rays
- Bearish/panic → lighthouse in storm, meditation at cliff's edge, lotus rising from mud
- Sideways/uncertain → peaks in mist, ripples on a still lake, a path through fog
- Always include: Zen/meditation element + natural landscape + dramatic lighting

Generate:
1. A detailed Midjourney prompt (English, include --ar {aspect_ratio} --style raw)
2. A simplified DALL-E prompt (English, descriptive)
3. A Chinese description of the scene (for designer reference)

Output in this format:
### Midjourney
<English prompt>
### DALL-E
<English prompt>
### 中文描述
<Chinese description>"""
