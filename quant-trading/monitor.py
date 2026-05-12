"""
实时监控模块 - 监控买入信号并推送飞书通知
"""
import pandas as pd
from strategy import dual_ma_strategy
from feishu_notify import FeishuNotifier

def scan_buy_signals(data_file='data/hs300_5y.parquet', webhook_url=None):
    """
    扫描所有股票的最新买入信号
    
    参数:
        data_file: 数据文件路径
        webhook_url: 飞书Webhook地址
    
    返回:
        买入信号列表
    """
    df = pd.read_parquet(data_file)
    df['date'] = pd.to_datetime(df['date'])
    
    buy_signals = []
    
    for stock_code in df['stock_code'].unique():
        stock_df = df[df['stock_code'] == stock_code].copy()
        stock_df = stock_df.sort_values('date').reset_index(drop=True)
        
        # 应用策略
        stock_df = dual_ma_strategy(stock_df)
        
        # 获取最新信号
        latest = stock_df.iloc[-1]
        if latest['position'] == 1:  # 买入信号
            buy_signals.append({
                'stock_code': stock_code,
                'price': latest['close'],
                'date': latest['date'].strftime('%Y-%m-%d')
            })
            
            # 发送飞书通知
            if webhook_url:
                notifier = FeishuNotifier(webhook_url)
                notifier.send_buy_signal(stock_code, latest['close'], latest['date'].strftime('%Y-%m-%d'))
    
    return buy_signals

if __name__ == '__main__':
    # 替换为你的飞书Webhook地址
    WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_KEY"
    
    print("开始扫描买入信号...")
    signals = scan_buy_signals(webhook_url=WEBHOOK_URL)
    
    print(f"\n共发现 {len(signals)} 个买入信号")
    for signal in signals:
        print(f"  {signal['stock_code']}: ¥{signal['price']:.2f} ({signal['date']})")
