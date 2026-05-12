"""
回测引擎 - 模拟交易并计算收益指标
"""
import pandas as pd
import numpy as np
from strategy import apply_strategy_to_all
from feishu_notify import FeishuNotifier

class BacktestEngine:
    def __init__(self, initial_capital=100000, commission_rate=0.0003, stamp_tax=0.001):
        """
        初始化回测引擎
        
        参数:
            initial_capital: 初始资金 (默认10万)
            commission_rate: 手续费率 (默认万分之三)
            stamp_tax: 印花税率 (默认千分之一，仅卖出)
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax = stamp_tax
        
    def run_backtest(self, df):
        """
        执行回测(处理停牌情况)
        
        参数:
            df: 包含策略信号的DataFrame
        """
        capital = self.initial_capital
        position = 0  # 持仓数量
        trades = []
        equity_curve = []
        
        for idx, row in df.iterrows():
            # 记录当前权益
            current_equity = capital + position * row['close']
            equity_curve.append({
                'date': row['date'],
                'equity': current_equity
            })
            
            # 停牌检测:成交量为0表示停牌,不能交易
            if row['volume'] == 0:
                continue
            
            # 交易信号
            if row['position'] == 1 and position == 0:  # 买入
                shares = int(capital * 0.95 / row['close'])  # 使用95%资金
                if shares > 0:
                    cost = shares * row['close']
                    commission = cost * self.commission_rate
                    total_cost = cost + commission
                    
                    if total_cost <= capital:
                        capital -= total_cost
                        position = shares
                        trades.append({
                            'date': row['date'],
                            'stock': row['stock_code'],
                            'action': 'buy',
                            'price': row['close'],
                            'shares': shares,
                            'cost': total_cost
                        })
            
            elif row['position'] == -1 and position > 0:  # 卖出
                revenue = position * row['close']
                commission = revenue * self.commission_rate
                tax = revenue * self.stamp_tax
                total_revenue = revenue - commission - tax
                
                capital += total_revenue
                trades.append({
                    'date': row['date'],
                    'stock': row['stock_code'],
                    'action': 'sell',
                    'price': row['close'],
                    'shares': position,
                    'revenue': total_revenue
                })
                position = 0
        
        # 最终权益
        final_equity = capital + position * df.iloc[-1]['close']
        
        return {
            'trades': pd.DataFrame(trades),
            'equity_curve': pd.DataFrame(equity_curve),
            'final_equity': final_equity
        }
    
    def calculate_metrics(self, equity_curve, final_equity):
        """
        计算回测指标
        """
        # 总收益率
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        # 年化收益率
        days = (equity_curve['date'].max() - equity_curve['date'].min()).days
        years = days / 365
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # 最大回撤
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak']
        max_drawdown = equity_curve['drawdown'].min()
        
        return {
            '总收益率': f"{total_return:.2%}",
            '年化收益率': f"{annual_return:.2%}",
            '最大回撤': f"{max_drawdown:.2%}",
            '初始资金': f"¥{self.initial_capital:,.0f}",
            '最终资金': f"¥{final_equity:,.0f}"
        }

def run_single_stock_backtest(stock_code, data_file='data/hs300_5y.parquet'):
    """
    对单只股票进行回测
    """
    # 加载数据
    df = pd.read_parquet(data_file)
    df['date'] = pd.to_datetime(df['date'])
    
    # 筛选股票
    stock_df = df[df['stock_code'] == stock_code].copy()
    stock_df = stock_df.sort_values('date').reset_index(drop=True)
    
    # 应用策略
    from strategy import dual_ma_strategy
    stock_df = dual_ma_strategy(stock_df)
    
    # 执行回测
    engine = BacktestEngine()
    result = engine.run_backtest(stock_df)
    metrics = engine.calculate_metrics(result['equity_curve'], result['final_equity'])
    
    return result, metrics

if __name__ == '__main__':
    print("=" * 50)
    print("A股量化交易回测系统")
    print("=" * 50)
    
    # 示例：对第一只股票进行回测
    df = pd.read_parquet('data/hs300_5y.parquet')
    test_stock = df['stock_code'].iloc[0]
    
    print(f"\n测试股票: {test_stock}")
    result, metrics = run_single_stock_backtest(test_stock)
    
    print("\n回测结果:")
    print("-" * 50)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    print(f"\n交易次数: {len(result['trades'])}")
    if len(result['trades']) > 0:
        print("\n最近5笔交易:")
        print(result['trades'].tail())
