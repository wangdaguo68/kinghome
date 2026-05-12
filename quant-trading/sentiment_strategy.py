"""
舆情监控+大单跟随策略 - 基于新闻事件和资金流向的智能交易
"""
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
from pathlib import Path
import re

class SentimentStrategy:
    def __init__(self, model_path='models/sentiment_model.pkl'):
        self.model_path = model_path
        self.model = None
        self.vectorizer = None
        self.hot_stocks = {}
        
    def fetch_news_sources(self):
        """获取多源新闻数据"""
        news_data = []
        
        # 东方财富热门新闻
        try:
            df = ak.stock_news_em()
            for _, row in df.iterrows():
                news_data.append({
                    'title': row['新闻标题'],
                    'content': row.get('新闻内容', ''),
                    'time': row['发布时间'],
                    'source': '东方财富',
                    'stocks': self.extract_stock_codes(row['新闻标题'])
                })
        except:
            pass
        
        # 财联社电报
        try:
            df = ak.stock_telegraph_cls()
            for _, row in df.iterrows():
                news_data.append({
                    'title': row['内容'],
                    'content': row['内容'],
                    'time': row['发布时间'],
                    'source': '财联社',
                    'stocks': self.extract_stock_codes(row['内容'])
                })
        except:
            pass
        
        return pd.DataFrame(news_data)
    
    def extract_stock_codes(self, text):
        """从文本中提取股票代码和名称"""
        codes = []
        # 匹配6位数字股票代码
        pattern = r'[0-9]{6}'
        matches = re.findall(pattern, text)
        codes.extend(matches)
        
        # 匹配股票简称（需要进一步查询转换为代码）
        # 这里简化处理，实际可调用 ak.stock_info_a_code_name() 进行匹配
        return list(set(codes))
    
    def analyze_sentiment(self, news_df):
        """分析新闻情绪并评分"""
        positive_keywords = ['利好', '上涨', '突破', '创新高', '增长', '盈利', '中标', '合作', '收购']
        negative_keywords = ['利空', '下跌', '破位', '亏损', '风险', '调查', '处罚', '退市']
        
        for idx, row in news_df.iterrows():
            text = row['title'] + ' ' + row['content']
            
            pos_score = sum(1 for kw in positive_keywords if kw in text)
            neg_score = sum(1 for kw in negative_keywords if kw in text)
            
            news_df.at[idx, 'sentiment_score'] = pos_score - neg_score
            news_df.at[idx, 'is_major_event'] = self.is_major_event(text)
        
        return news_df
    
    def is_major_event(self, text):
        """判断是否为重大事件"""
        major_keywords = ['重组', '并购', '中标', '业绩', '分红', '增持', '回购', '停牌', '复牌']
        return any(kw in text for kw in major_keywords)
    
    def detect_big_orders(self, symbol):
        """检测大单异动"""
        try:
            # 获取实时资金流
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            stock_flow = df[df['代码'] == symbol]
            
            if stock_flow.empty:
                return None
            
            row = stock_flow.iloc[0]
            return {
                'symbol': symbol,
                'main_net_inflow': row['主力净流入-净额'],
                'main_net_inflow_pct': row['主力净流入-净占比'],
                'super_large_inflow': row['超大单净流入-净额'],
                'large_inflow': row['大单净流入-净额'],
                'is_big_order': row['主力净流入-净占比'] > 5  # 主力净流入超过5%
            }
        except:
            return None
    
    def calculate_features(self, symbol, news_score, fund_flow):
        """计算综合特征"""
        features = {
            'sentiment_score': news_score,
            'main_inflow_pct': fund_flow['main_net_inflow_pct'] if fund_flow else 0,
            'super_large_inflow': fund_flow['super_large_inflow'] if fund_flow else 0,
        }
        
        # 获取技术指标
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            df = df.tail(60)
            
            features['ma5'] = df['收盘'].rolling(5).mean().iloc[-1]
            features['ma20'] = df['收盘'].rolling(20).mean().iloc[-1]
            features['volume_ratio'] = df['成交量'].iloc[-1] / df['成交量'].rolling(5).mean().iloc[-1]
            features['price_change'] = df['收盘'].pct_change().iloc[-1]
        except:
            features.update({'ma5': 0, 'ma20': 0, 'volume_ratio': 1, 'price_change': 0})
        
        return features
    
    def train_model(self, training_data):
        """训练机器学习模型"""
        X = training_data.drop(['label', 'symbol'], axis=1)
        y = training_data['label']
        
        self.model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3)
        self.model.fit(X, y)
        
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({'model': self.model, 'features': X.columns.tolist()}, self.model_path)
    
    def predict_signal(self, symbol):
        """预测交易信号"""
        if self.model is None:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
        
        # 获取新闻情绪
        news = self.fetch_news_sources()
        news = self.analyze_sentiment(news)
        stock_news = news[news['stocks'].apply(lambda x: symbol in x)]
        news_score = stock_news['sentiment_score'].mean() if not stock_news.empty else 0
        
        # 检测大单
        fund_flow = self.detect_big_orders(symbol)
        
        if fund_flow and fund_flow['is_big_order']:
            features = self.calculate_features(symbol, news_score, fund_flow)
            X = pd.DataFrame([features])
            
            prediction = self.model.predict(X)[0]
            probability = self.model.predict_proba(X)[0]
            
            return {
                'symbol': symbol,
                'action': '买入' if prediction == 1 else '观望',
                'confidence': max(probability),
                'news_score': news_score,
                'main_inflow_pct': fund_flow['main_net_inflow_pct'],
                'reason': f"舆情评分{news_score:.1f}, 主力净流入{fund_flow['main_net_inflow_pct']:.2f}%"
            }
        
        return None
    
    def monitor_and_alert(self, stock_pool, callback=None):
        """监控股票池并发出交易信号"""
        signals = []
        
        for symbol in stock_pool:
            signal = self.predict_signal(symbol)
            if signal and signal['action'] == '买入':
                signals.append(signal)
                if callback:
                    callback(signal)
        
        return signals
