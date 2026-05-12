"""
舆情监控策略使用示例
"""
from sentiment_strategy import SentimentStrategy
from feishu_notify import FeishuNotifier

# 初始化策略
strategy = SentimentStrategy()

# 监控股票池
stock_pool = ['000001', '600519', '000858', '600036']

# 设置飞书通知
notifier = FeishuNotifier('your_webhook_url')

def on_signal(signal):
    """收到交易信号时的回调"""
    message = f"""
    【舆情交易信号】
    股票: {signal['symbol']}
    操作: {signal['action']}
    置信度: {signal['confidence']:.2%}
    原因: {signal['reason']}
    """
    print(message)
    notifier.send_message(message)

# 执行监控
print("开始监控舆情和大单...")
signals = strategy.monitor_and_alert(stock_pool, callback=on_signal)

print(f"\n共发现 {len(signals)} 个交易机会")
for sig in signals:
    print(f"{sig['symbol']}: {sig['action']} (置信度: {sig['confidence']:.2%})")
