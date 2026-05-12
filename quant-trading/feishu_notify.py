"""
飞书Webhook通知模块
"""
import requests
import json

class FeishuNotifier:
    def __init__(self, webhook_url):
        """
        初始化飞书通知器
        
        参数:
            webhook_url: 飞书机器人Webhook地址
        """
        self.webhook_url = webhook_url
    
    def send_buy_signal(self, stock_code, price, date):
        """
        发送买入信号通知
        
        参数:
            stock_code: 股票代码
            price: 买入价格
            date: 信号日期
        """
        message = {
            "msg_type": "text",
            "content": {
                "text": f"📈 买入信号提醒\n\n股票代码: {stock_code}\n买入价格: ¥{price:.2f}\n信号日期: {date}\n\n请注意风险,仅供参考!"
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(message)
            )
            
            if response.status_code == 200:
                print(f"✓ 飞书通知发送成功: {stock_code}")
            else:
                print(f"✗ 飞书通知发送失败: {response.text}")
        except Exception as e:
            print(f"✗ 飞书通知异常: {e}")
    
    def send_summary(self, total_signals, stock_list):
        """
        发送汇总通知
        
        参数:
            total_signals: 信号总数
            stock_list: 股票列表
        """
        stocks_text = "\n".join([f"• {code}" for code in stock_list[:10]])
        if len(stock_list) > 10:
            stocks_text += f"\n... 还有 {len(stock_list) - 10} 只"
        
        message = {
            "msg_type": "text",
            "content": {
                "text": f"📊 今日买入信号汇总\n\n信号数量: {total_signals}\n\n股票列表:\n{stocks_text}"
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(message)
            )
            
            if response.status_code == 200:
                print(f"✓ 汇总通知发送成功")
            else:
                print(f"✗ 汇总通知发送失败: {response.text}")
        except Exception as e:
            print(f"✗ 汇总通知异常: {e}")

# 使用示例
if __name__ == '__main__':
    # 替换为你的飞书Webhook地址
    WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/1c08a243-950d-420f-9bd3-ac7ebec3cb81"
    
    notifier = FeishuNotifier(WEBHOOK_URL)
    
    # 测试发送
    notifier.send_buy_signal("600000", 12.50, "2026-03-12")
