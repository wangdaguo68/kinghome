"""
测试飞书通知
"""
from feishu_notify import FeishuNotifier

# 你的Webhook地址
WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/1c08a243-950d-420f-9bd3-ac7ebec3cb81"

# 创建通知器
notifier = FeishuNotifier(WEBHOOK_URL)

# 测试发送买入信号
print("正在发送测试通知...")
notifier.send_buy_signal('600000', 12.50, '2026-03-12')

# 测试发送汇总通知
print("\n正在发送汇总通知...")
notifier.send_summary(3, ['600000', '600036', '601318'])

print("\n测试完成！请检查你的飞书群是否收到消息。")
