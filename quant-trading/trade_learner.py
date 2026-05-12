"""
交易模式学习模块 - 从历史成交记录学习个人交易偏好
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
from pathlib import Path
import akshare as ak
from datetime import datetime, timedelta

class TradeLearner:
    def __init__(self, model_path='models/trade_pattern_model.pkl'):
        self.model_path = model_path
        self.model = None
        self.feature_columns = None
        
    def load_trade_history(self, excel_path):
        """
        加载历史成交记录
        
        Excel格式要求:
        - 股票代码 (如: 000001.SZ)
        - 交易方向 (买入/卖出)
        - 成交时间 (YYYY-MM-DD HH:MM:SS)
        - 成交价格
        - 成交量
        """
        df = pd.read_excel(excel_path)
        df['成交时间'] = pd.to_datetime(df['成交时间'])
        df['交易标签'] = df['交易方向'].map({'买入': 1, '卖出': 0})
        return df
    
    def prepare_training_data(self, trade_history_path):
        """准备训练数据：关联历史成交与分钟行情"""
        trades = self.load_trade_history(trade_history_path)
        training_data = []
        
        for idx, trade in trades.iterrows():
            symbol = trade['股票代码']
            trade_time = trade['成交时间']
            
            minute_data = self.fetch_minute_data(symbol, trade_time.date())
            if minute_data is None:
                continue
            
            minute_data = self.calculate_features(minute_data)
            
            trade_minute = minute_data[minute_data['时间'] <= trade_time].iloc[-1]
            
            features = {
                'ma5': trade_minute['ma5'],
                'ma10': trade_minute['ma10'],
                'ma20': trade_minute['ma20'],
                'rsi': trade_minute['rsi'],
                'volume_ratio': trade_minute['volume_ratio'],
                'price_change': trade_minute['price_change'],
                'price_change_5': trade_minute['price_change_5'],
                'label': trade['交易标签']
            }
            training_data.append(features)
        
        return pd.DataFrame(training_data)
    
    def train_model(self, training_data):
        """训练分类模型"""
        X = training_data.drop('label', axis=1)
        y = training_data['label']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        self.feature_columns = X.columns.tolist()
        
        y_pred = self.model.predict(X_test)
        print(classification_report(y_test, y_pred, target_names=['卖出', '买入']))
        
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({'model': self.model, 'features': self.feature_columns}, self.model_path)
    
    def predict(self, market_data):
        """预测买卖倾向"""
        if self.model is None:
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.feature_columns = model_data['features']
        
        features = self.calculate_features(market_data)
        X = features[self.feature_columns].iloc[-1:].fillna(0)
        
        prediction = self.model.predict(X)[0]
        probability = self.model.predict_proba(X)[0]
        
        return {'action': '买入' if prediction == 1 else '卖出', 
                'confidence': max(probability)}
    
    def fetch_minute_data(self, symbol, date):
        """获取指定日期的分钟级行情数据"""
        try:
            df = ak.stock_zh_a_hist_min_em(symbol=symbol, period='1', 
                                           start_date=date.strftime('%Y-%m-%d 09:30:00'),
                                           end_date=date.strftime('%Y-%m-%d 15:00:00'))
            return df
        except:
            return None
    
    def calculate_features(self, df):
        """计算技术指标特征"""
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain / loss))
        
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(5).mean()
        df['price_change'] = df['close'].pct_change()
        df['price_change_5'] = df['close'].pct_change(5)
        
        return df
