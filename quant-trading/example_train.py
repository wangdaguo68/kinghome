"""
交易模式学习示例 - 训练和使用个人交易模式模型
"""
from trade_learner import TradeLearner

# 1. 训练模型
learner = TradeLearner()

# 从历史成交记录准备训练数据
print("正在加载历史成交记录并关联分钟行情...")
training_data = learner.prepare_training_data('trade_history.xlsx')

print(f"成功准备 {len(training_data)} 条训练样本")
print("\n训练数据预览:")
print(training_data.head())

# 训练模型
print("\n开始训练模型...")
learner.train_model(training_data)
print("模型训练完成！")

# 2. 使用模型预测
print("\n使用模型预测当前行情...")
import akshare as ak

# 获取实时数据
current_data = ak.stock_zh_a_hist_min_em(symbol='000001', period='1')
prediction = learner.predict(current_data)

print(f"预测结果: {prediction['action']}")
print(f"置信度: {prediction['confidence']:.2%}")
