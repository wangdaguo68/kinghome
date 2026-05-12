# A股量化交易系统

轻量级量化交易项目，基于沪深300成分股的双均线策略回测系统。

## 功能特点

- 数据获取：使用 akshare 获取沪深300成分股近5年日线数据
- 策略实现：双均线策略 (MA20/MA60)，使用 pandas 向量化操作
- 回测引擎：模拟真实交易，考虑手续费和印花税
- 性能指标：总收益率、年化收益率、最大回撤

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方式1：交互式运行

```bash
python main.py
```

### 方式2：独立模块运行

```bash
# 1. 下载数据
python data.py

# 2. 测试策略
python strategy.py

# 3. 运行回测
python engine.py
```

## 项目结构

```
quant-trading/
├── data.py          # 数据获取模块
├── strategy.py      # 策略模块
├── engine.py        # 回测引擎
├── main.py          # 主程序入口
├── requirements.txt # 依赖包
└── data/            # 数据存储目录
    └── hs300_5y.parquet
```

## 策略说明

双均线策略：
- 计算20日均线 (MA20) 和60日均线 (MA60)
- MA20向上突破MA60时买入
- MA20向下突破MA60时卖出

## 回测参数

- 初始资金：10万元
- 手续费：万分之三 (0.03%)
- 印花税：千分之一 (0.1%，仅卖出)
- 每次使用95%可用资金

## 二次开发

代码结构清晰，易于扩展：
- 修改 `strategy.py` 实现新策略
- 调整 `engine.py` 中的交易逻辑
- 在 `data.py` 中添加更多数据源
