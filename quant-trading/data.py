"""
数据获取模块 - 获取沪深300成分股历史数据
"""
import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

def get_hs300_stocks():
    """获取沪深300成分股列表"""
    df = ak.index_stock_cons_csindex(symbol="000300")
    return df['成分券代码'].tolist()

def get_stock_data(stock_code, start_date, end_date):
    """获取单只股票的日线数据(前复权)"""
    try:
        # 使用前复权数据(qfq)避免除权缺口
        df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                start_date=start_date, end_date=end_date, adjust="qfq")
        
        if df is not None and not df.empty:
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            })
            df['stock_code'] = stock_code
            df = df[['date', 'stock_code', 'open', 'high', 'low', 'close', 'volume']]
            return df
    except Exception as e:
        print(f"获取 {stock_code} 数据失败: {e}")
    return None

def download_all_data():
    """下载所有沪深300成分股数据"""
    # 计算日期范围（过去5年）
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y%m%d')
    
    print(f"开始下载数据: {start_date} 至 {end_date}")
    
    # 获取成分股列表
    stocks = get_hs300_stocks()
    print(f"共 {len(stocks)} 只股票")
    
    # 下载数据
    all_data = []
    for i, stock in enumerate(stocks, 1):
        print(f"[{i}/{len(stocks)}] 下载 {stock}")
        df = get_stock_data(stock, start_date, end_date)
        if df is not None:
            all_data.append(df)
    
    # 合并数据
    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        
        # 保存到本地
        Path('data').mkdir(exist_ok=True)
        output_file = 'data/hs300_5y.parquet'
        result.to_parquet(output_file, index=False)
        print(f"\n数据已保存至: {output_file}")
        print(f"总记录数: {len(result)}")
        return result
    else:
        print("未获取到任何数据")
        return None

if __name__ == '__main__':
    download_all_data()
