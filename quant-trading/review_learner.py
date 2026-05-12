"""
复盘学习模块 - 从飞书复盘文档学习交易经验
"""
import pandas as pd
import numpy as np
from datetime import datetime
import requests
import json
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import joblib
from pathlib import Path

class ReviewLearner:
    def __init__(self, feishu_app_id, feishu_app_secret, model_path='models/review_model.pkl'):
        """
        初始化复盘学习器
        
        参数:
            feishu_app_id: 飞书应用ID
            feishu_app_secret: 飞书应用密钥
            model_path: 模型保存路径
        """
        self.app_id = feishu_app_id
        self.app_secret = feishu_app_secret
        self.access_token = None
        self.model_path = model_path
        self.model = None
        self.vectorizer = TfidfVectorizer(max_features=100)
        
    def get_access_token(self):
        """获取飞书访问令牌"""
        url = "https://open.feishu.cn/open-api/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            self.access_token = response.json()['tenant_access_token']
            return self.access_token
        return None
    
    def fetch_review_docs(self, folder_token, days=30):
        """从飞书文档获取复盘内容"""
        if not self.access_token:
            self.get_access_token()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        # 获取文件夹下的文档列表
        url = f"https://open.feishu.cn/open-api/drive/v1/files?folder_token={folder_token}"
        response = requests.get(url, headers=headers)
        
        reviews = []
        if response.status_code == 200:
            files = response.json().get('data', {}).get('files', [])
            
            for file in files:
                if file['type'] == 'doc':
                    doc_content = self.get_doc_content(file['token'])
                    if doc_content:
                        reviews.append({
                            'date': self.extract_date(file['name']),
                            'title': file['name'],
                            'content': doc_content,
                            'doc_token': file['token']
                        })
        
        return pd.DataFrame(reviews)
    
    def get_doc_content(self, doc_token):
        """获取文档内容"""
        if not self.access_token:
            self.get_access_token()
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://open.feishu.cn/open-api/docx/v1/documents/{doc_token}/raw_content"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('data', {}).get('content', '')
        return None
    
    def extract_date(self, filename):
        """从文件名提取日期"""
        pattern = r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})'
        match = re.search(pattern, filename)
        if match:
            date_str = match.group(1).replace('年', '-').replace('月', '-').replace('日', '')
            return pd.to_datetime(date_str)
        return datetime.now()
    
    def parse_review_content(self, content):
        """解析复盘内容，提取关键信息"""
        parsed = {
            'stocks_mentioned': [],
            'success_trades': [],
            'failed_trades': [],
            'lessons': [],
            'sentiment': 0
        }
        
        # 提取股票代码
        stock_pattern = r'[0-9]{6}'
        parsed['stocks_mentioned'] = list(set(re.findall(stock_pattern, content)))
        
        # 提取成功/失败案例
        if '成功' in content or '盈利' in content or '赚' in content:
            parsed['success_trades'] = self.extract_trade_cases(content, positive=True)
        if '失败' in content or '亏损' in content or '错误' in content:
            parsed['failed_trades'] = self.extract_trade_cases(content, positive=False)
        
        # 情绪评分
        positive_words = ['成功', '盈利', '正确', '把握', '机会']
        negative_words = ['失败', '亏损', '错误', '失误', '后悔']
        parsed['sentiment'] = sum(1 for w in positive_words if w in content) - sum(1 for w in negative_words if w in content)
        
        return parsed
    
    def extract_trade_cases(self, content, positive=True):
        """提取交易案例"""
        cases = []
        lines = content.split('\n')
        
        for line in lines:
            if positive and any(kw in line for kw in ['成功', '盈利', '赚']):
                stock_codes = re.findall(r'[0-9]{6}', line)
                if stock_codes:
                    cases.append({'stock': stock_codes[0], 'result': 'success', 'note': line})
            elif not positive and any(kw in line for kw in ['失败', '亏损', '错']):
                stock_codes = re.findall(r'[0-9]{6}', line)
                if stock_codes:
                    cases.append({'stock': stock_codes[0], 'result': 'fail', 'note': line})
        
        return cases
