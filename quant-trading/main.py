"""
A股量化交易系统 - 主程序
"""
import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("A股量化交易系统 - 沪深300双均线策略")
    print("=" * 60)
    
    print("\n请选择操作:")
    print("1. 下载数据 (沪深300成分股近5年数据)")
    print("2. 运行策略回测 (单只股票)")
    print("3. 批量回测 (所有股票)")
    print("4. 扫描买入信号并推送飞书通知")
    print("0. 退出")
    
    choice = input("\n请输入选项: ").strip()
    
    if choice == '1':
        print("\n开始下载数据...")
        from data import download_all_data
        download_all_data()
        
    elif choice == '2':
        if not Path('data/hs300_5y.parquet').exists():
            print("\n错误: 数据文件不存在，请先执行选项1下载数据")
            return
        
        stock_code = input("\n请输入股票代码 (如 600000): ").strip()
        print(f"\n正在回测 {stock_code}...")
        
        from engine import run_single_stock_backtest
        result, metrics = run_single_stock_backtest(stock_code)
        
        print("\n" + "=" * 60)
        print("回测结果")
        print("=" * 60)
        for key, value in metrics.items():
            print(f"{key}: {value}")
        
        print(f"\n交易次数: {len(result['trades'])}")
        if len(result['trades']) > 0:
            print("\n最近5笔交易:")
            print(result['trades'].tail().to_string(index=False))
        
    elif choice == '3':
        if not Path('data/hs300_5y.parquet').exists():
            print("\n错误: 数据文件不存在，请先执行选项1下载数据")
            return
        
        print("\n开始批量回测...")
        import pandas as pd
        from engine import run_single_stock_backtest
        
        df = pd.read_parquet('data/hs300_5y.parquet')
        stocks = df['stock_code'].unique()[:10]  # 测试前10只
        
        results = []
        for i, stock in enumerate(stocks, 1):
            print(f"[{i}/{len(stocks)}] 回测 {stock}")
            try:
                _, metrics = run_single_stock_backtest(stock)
                results.append({
                    'stock_code': stock,
                    **metrics
                })
            except Exception as e:
                print(f"  失败: {e}")
        
        if results:
            result_df = pd.DataFrame(results)
            print("\n" + "=" * 60)
            print("批量回测结果")
            print("=" * 60)
            print(result_df.to_string(index=False))
    
    elif choice == '4':
        if not Path('data/hs300_5y.parquet').exists():
            print("\n错误: 数据文件不存在，请先执行选项1下载数据")
            return
        
        webhook_url = input("\n请输入飞书Webhook地址: ").strip()
        if not webhook_url:
            print("\n错误: Webhook地址不能为空")
            return
        
        print("\n开始扫描买入信号...")
        from monitor import scan_buy_signals
        signals = scan_buy_signals(webhook_url=webhook_url)
        
        print(f"\n共发现 {len(signals)} 个买入信号")
        if signals:
            print("\n信号详情:")
            for signal in signals:
                print(f"  {signal['stock_code']}: ¥{signal['price']:.2f} ({signal['date']})")
        
    elif choice == '0':
        print("\n再见!")
        sys.exit(0)
    else:
        print("\n无效选项")

if __name__ == '__main__':
    main()
