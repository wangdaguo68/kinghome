"""
策略模块 - 双均线策略
"""
import pandas as pd

def dual_ma_strategy(df, short_window=20, long_window=60):
    """
    双均线策略
    
    参数:
        df: 包含价格数据的DataFrame (必须有'close'列)
        short_window: 短期均线窗口 (默认20日)
        long_window: 长期均线窗口 (默认60日)
    
    返回:
        添加了信号列的DataFrame
    """
    # 计算均线
    df['ma_short'] = df['close'].rolling(window=short_window).mean()
    df['ma_long'] = df['close'].rolling(window=long_window).mean()
    
    # 生成信号 (向量化操作)
    df['signal'] = 0
    df.loc[df['ma_short'] > df['ma_long'], 'signal'] = 1  # 买入信号
    df.loc[df['ma_short'] < df['ma_long'], 'signal'] = -1  # 卖出信号
    
    # 检测突破点 (信号变化时才交易)
    df['position'] = df['signal'].diff()
    
    return df

def apply_strategy_to_all(data_file='data/hs300_5y.parquet'):
    """
    对所有股票应用策略
    """
    df = pd.read_parquet(data_file)
    df['date'] = pd.to_datetime(df['date'])
    
    results = []
    for stock_code in df['stock_code'].unique():
        stock_df = df[df['stock_code'] == stock_code].copy()
        stock_df = stock_df.sort_values('date')
        stock_df = dual_ma_strategy(stock_df)
        results.append(stock_df)
    
    return pd.concat(results, ignore_index=True)

if __name__ == '__main__':
    result = apply_strategy_to_all()
    print(f"策略计算完成，共 {len(result)} 条记录")
    print(f"\n买入信号数: {(result['position'] == 1).sum()}")
    print(f"卖出信号数: {(result['position'] == -1).sum()}")
