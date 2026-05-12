"""
机器学习策略模块 - 基于技术指标的买卖信号预测
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
from pathlib import Path

class MLStrategy:
    def __init__(self, model_path='models/ml_model.pkl'):
        """
        初始化机器学习策略
        
        参数:
            model_path: 模型保存路径
        """
        self.model_path = model_path
        self.model = None
        
    def calculate_features(self, df):
        """
        计算技术指标特征
        
        参数:
            df: 包含OHLCV数据的DataFrame
        
        返回:
            添加了特征列的DataFrame
        """
        # 移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # RSI指标
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD指标
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # 布林带
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # 成交量变化
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma5']
        
        # 价格变化率
        df['price_change'] = df['close'].pct_change()
        df['price_change_5d'] = df['close'].pct_change(periods=5)
        
        return df
