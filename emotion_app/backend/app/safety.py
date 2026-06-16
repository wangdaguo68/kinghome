RISK_KEYWORDS = (
    "想死",
    "不想活",
    "自杀",
    "自残",
    "伤害别人",
    "杀人",
    "活不下去",
    "结束生命",
)

SAFETY_REPLY = (
    "我很担心你现在的状态。如果你此刻有伤害自己的冲动，请马上联系身边可信任的人，"
    "或拨打当地紧急求助电话。你不需要一个人扛着这件事。"
)


def has_safety_risk(text: str) -> bool:
    normalized = text.replace(" ", "").lower()
    return any(keyword in normalized for keyword in RISK_KEYWORDS)

