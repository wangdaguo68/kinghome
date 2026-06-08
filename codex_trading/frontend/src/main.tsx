import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Activity, BarChart3, BellRing, BookOpenText, CalendarCheck, CalendarDays, ChevronLeft, ChevronRight, Clock3, Database, FileText, FlaskConical, Globe2, Newspaper, Radar, RefreshCw, Search, ShieldCheck, Zap } from "lucide-react";
import "./styles.css";

const API_HOST = window.location.hostname || "127.0.0.1";
const API_BASE = `${window.location.protocol}//${API_HOST}:19093`;
const FRONTEND_PORT_HINT = "19092";

type PageId = "calendar" | "research" | "cycle" | "tomorrow" | "intraday" | "live" | "strategy" | "backtest" | "risk" | "data" | "ledger";

type CycleState = {
  trade_date: string;
  red_count: number;
  down_count: number;
  limit_up_count: number;
  limit_down_count: number;
  turnover_billion: number;
  sh_turnover_billion: number;
  sz_turnover_billion: number;
  ma3: number;
  ma5: number;
  ma3_trend: string;
  ma5_trend: string;
  tag: string;
};

type Trade = {
  signal_date: string;
  entry_date: string;
  exit_date: string;
  symbol: string;
  name: string;
  pattern: string;
  cycle_tag: string;
  entry_price: number;
  exit_price: number;
  position_pct: number;
  pnl_pct: number;
  exit_reason: string;
  signal_reason: string;
  after_3d_return_pct: number | null;
  gross_pnl_pct?: number | null;
  fee_pct?: number;
  fee_amount?: number;
};

type BacktestResponse = {
  source: string;
  latest_date?: string | null;
  last_completed_entry_date?: string | null;
  range_days?: number;
  completion_note?: string;
  recent_market_days?: MarketCoverageDay[];
  metrics: Record<string, number>;
  trades: Trade[];
  rejected_count: number;
};

type EnergyBacktestResponse = BacktestResponse & {
  strategy: {
    id: string;
    name: string;
    description: string;
  };
  quality: QualityBreakdown;
  reflection: TradeReflection;
};

type StrategyBacktestResponse = EnergyBacktestResponse;

type MarketCoverageDay = {
  trade_date: string;
  red_count: number;
  down_count: number;
  limit_up_count: number;
  limit_down_count: number;
  turnover_billion: number;
  sh_turnover_billion: number;
  sz_turnover_billion: number;
};

type FeeModel = {
  source: string;
  sample_count: number;
  min_commission: number;
  commission_rate: number;
  commission_rate_upper_bound: number;
  stamp_tax_rate: number;
  transfer_fee_rate: number;
};

type StrategyExperiment = {
  id: string;
  name: string;
  description: string;
  settings: {
    amount_min_billion: number;
    rank_limit: number;
    first_limit_mode: string;
    one_to_two_open_min_pct: number;
    cycle_filter: boolean;
    position_pct?: number | null;
    max_signals_per_strategy?: number;
    research_only?: boolean;
    include_energy?: boolean;
  };
  metrics: Record<string, number>;
  trade_count: number;
  sample_trades: Trade[];
  trades: Trade[];
  quality: QualityBreakdown;
  reflection: TradeReflection;
  rejected_count: number;
};

type StrategyExperimentsResponse = {
  source: string;
  range_days: number;
  latest_date?: string | null;
  last_completed_entry_date?: string | null;
  completion_note?: string;
  recent_market_days?: MarketCoverageDay[];
  experiments: StrategyExperiment[];
};

type QualityRow = {
  key: string;
  metrics: Record<string, number>;
};

type QualityBreakdown = {
  by_pattern: QualityRow[];
  by_month: QualityRow[];
  by_board: QualityRow[];
};

type TradeReflection = {
  verdict: string;
  confidence: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
};

type TomorrowSignal = {
  signal_date: string;
  planned_entry_date: string | null;
  symbol: string;
  name: string;
  pattern: string;
  cycle_tag: string;
  planned_position_pct: number;
  stop_loss_pct: number;
  score: number;
  reason: string;
  execution_rule: string;
  close_price: number;
  close_pct: number;
  high_pct: number;
  amount_billion: number;
  sector_rank: number;
  limit_up: boolean;
  first_limit: boolean;
  consecutive_limits: number;
};

type TomorrowPlan = {
  id: string;
  name: string;
  description: string;
  settings: StrategyExperiment["settings"];
  version_id: string;
  version_eligible: boolean;
  version_verdict: string;
  version_reasons: string[];
  signals: TomorrowSignal[];
  rejected_count: number;
};

type TomorrowPlanResponse = {
  source: string;
  decision_date: string;
  planned_entry_date: string | null;
  cycle_tag: string;
  strategy_version_generated_at?: string;
  plans: TomorrowPlan[];
};

type AlertStatus = {
  feishu: {
    enabled: boolean;
    configured: boolean;
    chat_id: string;
    mode: string;
  };
  qmt: {
    enabled: boolean;
    mode: string;
    broker: string;
    message: string;
  };
};

type TrackedSignal = {
  id: string;
  status: string;
  created_at: string;
  updated_at: string;
  preset_name: string;
  version_id: string;
  signal_date: string;
  planned_entry_date: string | null;
  symbol: string;
  name: string;
  pattern: string;
  reference_price: number;
  last_price: number;
  last_pnl_pct: number;
  max_pnl_pct: number;
  min_pnl_pct: number;
  planned_position_pct: number;
  stop_loss_pct: number;
  take_profit_pct: number;
  execution_rule: string;
  exit_reason: string;
};

type TrackedSignalsResponse = {
  active_count: number;
  closed_count: number;
  tracks: TrackedSignal[];
};

type IntradaySignal = {
  id: string;
  scanned_at: string;
  symbol: string;
  name: string;
  pattern: string;
  trigger: string;
  cycle_tag: string | null;
  price: number;
  pct: number;
  amount_billion: number;
  sector_rank: number;
  planned_position_pct: number;
  stop_loss_pct: number;
  score: number;
  execution_rule: string;
  source: string;
};

type IntradayScanResponse = {
  status: {
    provider: string;
    ready: boolean;
    realtime: boolean;
    message: string;
    poll_seconds: number;
  };
  scanned_at: string;
  cycle_tag: string | null;
  signal_count: number;
  signals: IntradaySignal[];
};

type OptimizationCandidate = {
  id: string;
  name: string;
  description: string;
  settings: StrategyExperiment["settings"];
  metrics: Record<string, number>;
  score: number;
  reflection: TradeReflection;
};

type OptimizationGroup = {
  base_id: string;
  base_name: string;
  candidates: OptimizationCandidate[];
};

type StrategyOptimizationResponse = {
  source: string;
  range_days: number;
  groups: OptimizationGroup[];
};

type StrategyVersion = {
  version_id: string;
  name: string;
  description: string;
  settings: StrategyExperiment["settings"];
  train: Record<string, number>;
  validation: Record<string, number>;
  recent: Record<string, number>;
  score: number;
  eligible: boolean;
  verdict: string;
  reasons: string[];
};

type StrategyVersionGroup = {
  base_id: string;
  base_name: string;
  recommended_version: StrategyVersion | null;
  versions: StrategyVersion[];
};

type StrategyVersionsResponse = {
  generated_at: string;
  source: string;
  range_days: number;
  segments: Record<string, { start: string | null; end: string | null; days: number }>;
  groups: StrategyVersionGroup[];
};

type PatternRow = {
  name: string;
  state: "OPEN" | "WATCH" | "LOCK";
  size: string;
  expectancy: string;
  fit: string;
};

type CalendarImpact = "high" | "medium" | "watch";

type InvestmentEvent = {
  date: string;
  title: string;
  detail: string;
  category: string;
  market: string;
  impact: CalendarImpact;
  source: string;
  source_url?: string;
  tags?: string[];
};

type InvestmentCalendarResponse = {
  source: string;
  source_status: Record<string, { ok: boolean; count: number; message: string }>;
  start_date: string;
  end_date: string;
  updated_at: string;
  event_count: number;
  events: InvestmentEvent[];
  warnings: string[];
};

type IndustryResearchItem = {
  id: number;
  title: string;
  summary: string;
  content: string;
  report_type: string;
  source_name: string;
  source_type: string;
  source_url: string;
  institution: string;
  author: string;
  industry: string;
  symbols: string[];
  tags: string[];
  published_at: string | null;
  crawled_at: string | null;
};

type IndustryResearchResponse = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  items: IndustryResearchItem[];
  warning: string;
};

type IndustryResearchStats = {
  total: number;
  today_count: number;
  source_count: number;
  latest_published_at: string | null;
  latest_crawled_at: string | null;
  warning: string;
};

type IndustryResearchSource = {
  name: string;
  source_type: string;
  url: string;
  enabled: boolean;
  last_sync_at: string | null;
  last_status: string;
  last_error: string;
};

type IndustryResearchSourcesResponse = {
  sources: IndustryResearchSource[];
  warning: string;
};

const navItems: Array<{ id: PageId; label: string; icon: React.ReactNode }> = [
  { id: "calendar", label: "投资日历", icon: <CalendarDays size={17} /> },
  { id: "research", label: "产业研报", icon: <Newspaper size={17} /> },
  { id: "cycle", label: "周期雷达", icon: <Activity size={17} /> },
  { id: "tomorrow", label: "明日策略", icon: <CalendarCheck size={17} /> },
  { id: "intraday", label: "盘中雷达", icon: <Radar size={17} /> },
  { id: "live", label: "实盘提醒", icon: <BellRing size={17} /> },
  { id: "strategy", label: "策略实验", icon: <FlaskConical size={17} /> },
  { id: "backtest", label: "回测报告", icon: <BarChart3 size={17} /> },
  { id: "risk", label: "风控执行", icon: <ShieldCheck size={17} /> },
  { id: "data", label: "行情数据", icon: <Database size={17} /> },
  { id: "ledger", label: "研究账本", icon: <BookOpenText size={17} /> },
];

const patterns: PatternRow[] = [
  { name: "极值套利", state: "OPEN", size: "8%", expectancy: "+2.4R", fit: "0.88" },
  { name: "首板打板", state: "OPEN", size: "6%", expectancy: "+1.1R", fit: "0.73" },
  { name: "一进二", state: "WATCH", size: "5%", expectancy: "+0.4R", fit: "0.51" },
  { name: "分歧低吸", state: "LOCK", size: "0%", expectancy: "二期", fit: "锁定" },
];

const investmentEvents: InvestmentEvent[] = [
  { date: "2026-06-01", title: "住友电木上调半导体封装材料价格", detail: "半导体封装用环氧树脂成形材料价格上调约 10%-20%，自 6 月 1 日起发货执行新价格。", category: "半导体", market: "日本 / 材料", impact: "medium", source: "产业公告整理" },
  { date: "2026-06-01", title: "美团公布 2026 年一季度业绩", detail: "董事会定于 6 月 1 日举行会议并公布 2026 年第一季度未经审核财务业绩。", category: "财报", market: "港股 / 互联网", impact: "high", source: "公司公告" },
  { date: "2026-06-01", title: "NVIDIA GTC Taipei 2026 开幕", detail: "大会于 6 月 1 日至 4 日举办，黄仁勋 6 月 1 日发表主题演讲，关注 AI 芯片、机器人与算力生态。", category: "AI", market: "美股 / 台股", impact: "high", source: "NVIDIA 官方活动" },
  { date: "2026-06-01", title: "宇树科技科创板 IPO 上会", detail: "机器人产业链核心事件，关注人形机器人、减速器、传感器与国产控制器映射。", category: "IPO", market: "A股 / 机器人", impact: "high", source: "交易所公告整理" },
  { date: "2026-06-01", title: "华为 nova 16 系列及全场景新品发布会", detail: "关注端侧 AI、鸿蒙生态、消费电子供应链和影像链条。", category: "消费电子", market: "A股 / 港股", impact: "medium", source: "公司活动" },
  { date: "2026-06-01", title: "北京市卫星物联网行业发展大会", detail: "大会在北京海淀举办，关注卫星通信、低轨组网、物联网终端与北斗应用。", category: "卫星互联网", market: "A股", impact: "medium", source: "会议公告" },
  { date: "2026-06-02", title: "台北电脑展 Computex 2026", detail: "6 月 2 日至 5 日举行，关注 AI PC、服务器、GPU、存储、电源与液冷产业链。", category: "AI硬件", market: "台股 / A股", impact: "high", source: "Computex 官方日程" },
  { date: "2026-06-02", title: "第四届天津国际航运产业博览会", detail: "6 月 2 日至 5 日举办，关注航运、港口、智能物流和船舶制造。", category: "航运", market: "A股", impact: "watch", source: "会议公告" },
  { date: "2026-06-02", title: "Microsoft Build 2026", detail: "6 月 2 日至 3 日在美国旧金山举行，关注 AI Agent、开发者工具、云服务与 Copilot 生态。", category: "AI软件", market: "美股 / 云计算", impact: "high", source: "Microsoft 官方活动" },
  { date: "2026-06-02", title: "2490 亿元 7 天期逆回购到期", detail: "关注央行公开市场操作续作规模、资金利率和短端流动性变化。", category: "流动性", market: "中国债市 / A股", impact: "medium", source: "公开市场到期整理" },
  { date: "2026-06-03", title: "广州国际数智装备与人工智能展", detail: "6 月 3 日至 5 日举办，关注工业 AI、智能装备、数控系统和机器视觉。", category: "高端制造", market: "A股", impact: "medium", source: "会议公告" },
  { date: "2026-06-03", title: "SNEC 光伏、储能及电池展", detail: "6 月 3 日至 5 日在上海举办，关注光伏新技术、储能、电池设备和电力电子。", category: "新能源", market: "A股", impact: "high", source: "会议公告" },
  { date: "2026-06-03", title: "圣彼得堡国际经济论坛", detail: "6 月 3 日至 6 日举行，关注能源、粮食、地缘贸易与大宗商品预期。", category: "宏观地缘", market: "全球", impact: "medium", source: "会议日程" },
  { date: "2026-06-04", title: "美联储公布经济状况褐皮书", detail: "观察美国消费、就业、薪资和物价描述，对降息预期和美元利率敏感。", category: "央行", market: "全球", impact: "high", source: "Federal Reserve 官方日历" },
  { date: "2026-06-04", title: "商务部新闻发布会", detail: "介绍近期商务领域重点工作，关注外贸、消费、跨境电商与反制措施表述。", category: "政策", market: "A股 / 港股", impact: "medium", source: "商务部发布" },
  { date: "2026-06-05", title: "美国 5 月非农就业报告", detail: "就业、失业率和薪资增速将影响美债收益率、美元和全球风险资产。", category: "宏观数据", market: "全球", impact: "high", source: "BLS 官方发布日程" },
  { date: "2026-06-05", title: "华为云创想者大会", detail: "6 月 5 日至 6 日举办，关注国产算力、云服务、行业大模型和昇腾生态。", category: "云计算", market: "A股", impact: "high", source: "公司活动" },
  { date: "2026-06-05", title: "中关村数字金融与金融安全大会", detail: "关注金融信创、数据安全、AI 金融应用和支付安全。", category: "金融科技", market: "A股", impact: "medium", source: "会议公告" },
  { date: "2026-06-05", title: "华北低空经济与人工智能科技博览会", detail: "6 月 5 日至 7 日举办，关注低空飞行器、空管系统、无人机和 AI 应用。", category: "低空经济", market: "A股", impact: "medium", source: "会议公告" },
  { date: "2026-06-06", title: "东风汽车 OpenVAN 无人物流车全球首发", detail: "关注无人配送、线控底盘、智能驾驶和商用车智能化链条。", category: "智能汽车", market: "A股 / 港股", impact: "medium", source: "公司活动" },
  { date: "2026-06-06", title: "首届人工智能高质量发展大会", detail: "关注 AI 应用落地、算力基础设施、数据要素和政策导向。", category: "AI", market: "A股", impact: "medium", source: "会议公告" },
  { date: "2026-06-08", title: "LME 下调铅锌直接合约单日涨跌幅限制", detail: "铅和锌直接合约单日涨跌幅限制从 15% 下调至 12%，6 月 8 日起生效。", category: "有色金属", market: "全球大宗", impact: "medium", source: "LME 规则公告" },
  { date: "2026-06-09", title: "Apple WWDC 2026", detail: "北京时间 6 月 9 日至 13 日举办，关注端侧 AI、iOS/macOS、MR 与苹果供应链。", category: "消费电子", market: "美股 / A股", impact: "high", source: "Apple 官方活动" },
  { date: "2026-06-09", title: "国际气体产业链展 IG China 2026", detail: "6 月 9 日至 11 日举办，关注电子特气、工业气体、半导体材料和装备。", category: "半导体材料", market: "A股", impact: "medium", source: "会议公告" },
  { date: "2026-06-10", title: "美国 5 月 CPI", detail: "通胀数据是 6 月 FOMC 前关键变量，影响降息定价、美债收益率和成长风格估值。", category: "宏观数据", market: "全球", impact: "high", source: "BLS 官方发布日程" },
  { date: "2026-06-10", title: "中国 5 月 CPI / PPI", detail: "关注价格修复、工业品通缩压力和政策加码预期。", category: "宏观数据", market: "A股 / 债市", impact: "high", source: "国家统计局发布日程" },
  { date: "2026-06-11", title: "美国 5 月 PPI", detail: "观察上游价格向核心 PCE 的传导，对美联储政策预期有二次验证意义。", category: "宏观数据", market: "全球", impact: "medium", source: "BLS 官方发布日程" },
  { date: "2026-06-12", title: "美国密歇根大学消费者信心初值", detail: "关注通胀预期和消费信心，对美元、黄金和风险偏好有短线影响。", category: "宏观数据", market: "全球", impact: "medium", source: "官方数据日程整理" },
  { date: "2026-06-15", title: "中国 5 月经济运行数据", detail: "工业增加值、社零、固定资产投资和地产链数据集中发布，验证内需修复强度。", category: "宏观数据", market: "A股 / 港股", impact: "high", source: "国家统计局发布日程" },
  { date: "2026-06-16", title: "美国 5 月零售销售", detail: "检验美国消费韧性，影响美元、美债和跨境电商、出口链预期。", category: "宏观数据", market: "全球", impact: "medium", source: "美国官方数据日程" },
  { date: "2026-06-16", title: "FOMC 议息会议开始", detail: "6 月 16 日至 17 日召开，关注点阵图、经济预测和鲍威尔措辞。", category: "央行", market: "全球", impact: "high", source: "Federal Reserve 官方日历" },
  { date: "2026-06-17", title: "美联储公布利率决议", detail: "关注联邦基金目标利率、点阵图、通胀和就业预测，冲击全球权益和商品。", category: "央行", market: "全球", impact: "high", source: "Federal Reserve 官方日历" },
  { date: "2026-06-18", title: "英国央行利率决议", detail: "关注英镑、欧洲风险偏好和全球央行政策节奏联动。", category: "央行", market: "欧洲", impact: "medium", source: "央行日程整理" },
  { date: "2026-06-20", title: "LPR 月度报价观察窗口", detail: "6 月 20 日为周六，关注顺延后的 1 年期和 5 年期以上 LPR 报价及地产政策信号。", category: "利率", market: "A股 / 债市", impact: "high", source: "中国货币网 / LPR 机制" },
  { date: "2026-06-22", title: "LPR 报价顺延关注日", detail: "若按工作日顺延，关注贷款市场报价利率是否调整，影响银行、地产、消费和久期资产。", category: "利率", market: "A股 / 港股", impact: "high", source: "中国货币网 / LPR 机制" },
  { date: "2026-06-23", title: "美国 6 月 S&P Global PMI 初值", detail: "制造业和服务业景气度初值，影响美债收益率和全球周期资产。", category: "宏观数据", market: "全球", impact: "medium", source: "数据日程整理" },
  { date: "2026-06-24", title: "英伟达股东大会观察窗口", detail: "关注 AI 算力供需、Blackwell / Rubin 节奏、数据中心资本开支和供应链指引。", category: "AI", market: "美股 / A股", impact: "medium", source: "公司日程整理" },
  { date: "2026-06-25", title: "美国一季度 GDP 终值", detail: "检验美国经济韧性，对降息路径和全球风险偏好有确认作用。", category: "宏观数据", market: "全球", impact: "medium", source: "BEA 官方发布日程" },
  { date: "2026-06-26", title: "美国 5 月 PCE 通胀", detail: "美联储最关注的通胀指标之一，核心 PCE 将影响 7 月政策预期。", category: "宏观数据", market: "全球", impact: "high", source: "BEA 官方发布日程" },
  { date: "2026-06-27", title: "周末政策与产业催化观察", detail: "关注国常会、部委政策、地方低空经济/机器人/算力项目落地公告。", category: "政策", market: "A股", impact: "watch", source: "周末公告跟踪" },
  { date: "2026-06-30", title: "中国 6 月官方 PMI", detail: "月末制造业、非制造业和综合 PMI 发布，观察内需、出口订单和价格分项。", category: "宏观数据", market: "A股 / 商品", impact: "high", source: "国家统计局发布日程" },
  { date: "2026-06-30", title: "半年末资金面与机构调仓", detail: "关注跨季流动性、基金半年报窗口、银行理财赎回和高低切换。", category: "资金面", market: "A股 / 债市", impact: "high", source: "市场日历整理" },
  { date: "2026-07-01", title: "下半年政策窗口开启", detail: "关注中报预告、政治局会议预期、行业政策和暑期消费链启动。", category: "政策", market: "A股 / 港股", impact: "medium", source: "市场日历整理" },
];

function stateClass(state: PatternRow["state"]) {
  return state === "OPEN" ? "positive" : state === "WATCH" ? "warning" : "negative";
}

function stateText(state: PatternRow["state"]) {
  if (state === "OPEN") return "启用";
  if (state === "WATCH") return "观察";
  return "锁定";
}

function sourceText(source?: string) {
  if (source === "tushare") return "Tushare 实盘历史数据";
  if (source === "demo") return "演示数据";
  return "读取中";
}

function patternText(pattern: string) {
  const map: Record<string, string> = {
    ExtremeArbitrage: "极值套利",
    FirstLimit: "首板打板",
    OneToTwo: "一进二",
    EnergyBreakout: "能量策略",
    ShortEnergy: "超短能量交易",
  };
  return map[pattern] ?? pattern;
}

function intradayPatternText(pattern: string) {
  const map: Record<string, string> = {
    IntradayFirstLimit: "盘中回封",
    IntradayStrongRepair: "强势修复",
  };
  return map[pattern] ?? pattern;
}

function cycleText(tag?: string) {
  const map: Record<string, string> = {
    IcePoint: "冰点",
    TurnUp: "拐点向上",
    MainRally: "主升浪",
    Climax: "高潮",
    TurnDown: "拐点向下",
    Downtrend: "退潮",
    LowShake: "低位震荡",
    HighShake: "高位震荡",
  };
  return tag ? map[tag] ?? tag : "-";
}

function trackStatusText(status: string) {
  const map: Record<string, string> = {
    notified: "已提醒",
    watching: "跟踪中",
    take_profit: "止盈",
    stop_loss: "止损",
    time_exit: "时间退出",
  };
  return map[status] ?? status;
}

function pct(value?: number | null) {
  if (value === undefined || value === null) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatBillion(value?: number | null) {
  if (value === undefined || value === null) return "-";
  return `${Math.round(value).toLocaleString("zh-CN")} 亿`;
}

function price(value?: number | null) {
  if (value === undefined || value === null) return "-";
  return value.toFixed(3);
}

function pnlClass(value: number) {
  return value >= 0 ? "cn-profit" : "cn-loss";
}

function modeText(value: string) {
  const map: Record<string, string> = {
    sealed: "收盘封板",
    touched_strong_close: "盘中触板 + 强收盘",
    strong_momentum: "强势接近涨停",
  };
  return map[value] ?? value;
}

function shortDate(value: string) {
  return value.slice(5);
}

function latest<T>(items: T[]): T | undefined {
  return items[items.length - 1];
}

function todayKey() {
  const value = new Date();
  const offset = value.getTimezoneOffset() * 60_000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 10);
}

function eventGroups(events: InvestmentEvent[]) {
  const groups = new Map<string, InvestmentEvent[]>();
  for (const event of events) {
    const rows = groups.get(event.date) ?? [];
    rows.push(event);
    groups.set(event.date, rows);
  }
  return [...groups.entries()].sort(([left], [right]) => left.localeCompare(right));
}

function weekdayText(value: string) {
  const names = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
  return names[new Date(`${value}T12:00:00`).getDay()];
}

function impactText(value: CalendarImpact) {
  const map: Record<CalendarImpact, string> = {
    high: "高影响",
    medium: "中影响",
    watch: "观察",
  };
  return map[value];
}

function calendarDates(startDate: string, endDate: string) {
  const start = new Date(`${startDate}T12:00:00`);
  const end = new Date(`${endDate}T12:00:00`);
  const length = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1);
  return Array.from({ length }, (_, index) => {
    const value = new Date(start);
    value.setDate(start.getDate() + index);
    return value.toISOString().slice(0, 10);
  });
}

function formatDateTime(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function App() {
  const [activePage, setActivePage] = useState<PageId>("calendar");
  const [cycles, setCycles] = useState<CycleState[]>([]);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [energyBacktest, setEnergyBacktest] = useState<EnergyBacktestResponse | null>(null);
  const [shortEnergyBacktest, setShortEnergyBacktest] = useState<StrategyBacktestResponse | null>(null);
  const [experiments, setExperiments] = useState<StrategyExperimentsResponse | null>(null);
  const [tomorrowPlan, setTomorrowPlan] = useState<TomorrowPlanResponse | null>(null);
  const [intradayScan, setIntradayScan] = useState<IntradayScanResponse | null>(null);
  const [alertStatus, setAlertStatus] = useState<AlertStatus | null>(null);
  const [trackedSignals, setTrackedSignals] = useState<TrackedSignalsResponse | null>(null);
  const [feeModel, setFeeModel] = useState<FeeModel | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>("尚未刷新");
  const [riskCheck, setRiskCheck] = useState<string>("等待预检");

  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cycleResponse, backtestResponse, tomorrowResponse, feeModelResponse] = await Promise.all([
        fetch(`${API_BASE}/api/cycles`),
        fetch(`${API_BASE}/api/backtest`),
        fetch(`${API_BASE}/api/tomorrow-plan`),
        fetch(`${API_BASE}/api/fee-model`),
      ]);
      if (!cycleResponse.ok || !backtestResponse.ok || !tomorrowResponse.ok || !feeModelResponse.ok) {
        const message = !cycleResponse.ok
          ? await cycleResponse.text()
          : !backtestResponse.ok
            ? await backtestResponse.text()
            : !tomorrowResponse.ok
              ? await tomorrowResponse.text()
              : await feeModelResponse.text();
        throw new Error(`后端 API 返回异常：${message}`);
      }
      setCycles(await cycleResponse.json());
      setBacktest(await backtestResponse.json());
      setTomorrowPlan(await tomorrowResponse.json());
      setFeeModel(await feeModelResponse.json());
      void fetch(`${API_BASE}/api/strategy-experiments`)
        .then((response) => (response.ok ? response.json() : Promise.reject(response)))
        .then(setExperiments)
        .catch(() => undefined);
      void fetch(`${API_BASE}/api/energy-backtest`)
        .then((response) => (response.ok ? response.json() : Promise.reject(response)))
        .then(setEnergyBacktest)
        .catch(() => undefined);
      void fetch(`${API_BASE}/api/short-energy-backtest`)
        .then((response) => (response.ok ? response.json() : Promise.reject(response)))
        .then(setShortEnergyBacktest)
        .catch(() => undefined);
      setLastRefresh(new Date().toLocaleTimeString("zh-CN", { hour12: false }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接后端 API");
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshLiveData = useCallback(async () => {
    const [statusResponse, trackedResponse, intradayResponse] = await Promise.all([
      fetch(`${API_BASE}/api/alerts/status`),
      fetch(`${API_BASE}/api/signals/tracked`),
      fetch(`${API_BASE}/api/intraday/scan`),
    ]);
    if (!statusResponse.ok || !trackedResponse.ok || !intradayResponse.ok) {
      throw new Error("提醒状态读取失败");
    }
    setAlertStatus(await statusResponse.json());
    setTrackedSignals(await trackedResponse.json());
    setIntradayScan(await intradayResponse.json());
  }, []);

  useEffect(() => {
    void refreshData();
  }, [refreshData]);

  useEffect(() => {
    void refreshLiveData().catch(() => undefined);
  }, [refreshLiveData]);

  const currentCycle = latest(cycles);
  const tradeCount = backtest?.metrics.trade_count ?? 0;
  const winRate = backtest?.metrics.win_rate_pct ?? 0;
  const currentGateState = currentCycle?.tag === "Downtrend" ? "锁定" : "通过";

  function runRiskCheck() {
    const blockedPatterns = patterns.filter((row) => row.state === "LOCK").length;
    const rejected = backtest?.rejected_count ?? 0;
    setRiskCheck(`预检完成：${patterns.length - blockedPatterns} 个模式可用，${blockedPatterns} 个锁定，${rejected} 个信号被风控拒绝`);
    setActivePage("risk");
  }

  return (
    <main className="shell">
      <aside className="rail">
        <div className="brand">
          <span className="mark">CL</span>
          <div>
            <strong>CycleLab</strong>
            <small>A 股短线量化</small>
          </div>
        </div>

        <nav>
          {navItems.map((item) => (
            <button
              className={activePage === item.id ? "active nav-button" : "nav-button"}
              key={item.id}
              onClick={() => setActivePage(item.id)}
              type="button"
            >
              {item.icon} {item.label}
            </button>
          ))}
        </nav>

        <section className="rail-card">
          <small>运行模式</small>
          <strong>模拟运行</strong>
          <span>{sourceText(backtest?.source)} · 实盘下单接口未启用</span>
        </section>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">接口地址：{API_BASE} · 前端端口：{FRONTEND_PORT_HINT} · 最近刷新：{lastRefresh}</p>
            <h1>{navItems.find((item) => item.id === activePage)?.label}</h1>
            <div className="demo-banner">数据源：{sourceText(backtest?.source)} · 最近一年 · 行情宽度按沪深 A 股统计（不含北交所） · 策略池排除科创板、北交所、ST · 不会真实下单</div>
          </div>
          <div className="top-actions">
            <button onClick={refreshData} type="button"><Zap size={16} /> {loading ? "刷新中" : "刷新数据"}</button>
            <button className="primary" onClick={runRiskCheck} type="button"><ShieldCheck size={16} /> 运行风控预检</button>
          </div>
        </header>

        {error && <div className="error-banner">{error}。如果你当前打开的是 19096 之类的旧前端地址，请改开 19092。后端固定在 19093。</div>}

        {activePage === "calendar" && <InvestmentCalendarPage />}
        {activePage === "research" && <IndustryResearchPage />}
        {activePage === "cycle" && (
          <>
            <section className="hero-grid">
              <div className="terminal-panel regime">
                <div className="panel-head">
                  <span>周期状态</span>
                  <b className={currentGateState === "通过" ? "positive" : "negative"}>{cycleText(currentCycle?.tag)}</b>
                </div>
                <div className="regime-number">{currentCycle?.red_count ?? "-"} <small>上涨家数</small></div>
                <div className="chart">
                  {cycles.map((point) => (
                    <div className="bar-wrap" key={point.trade_date}>
                      <div className="bar" style={{ height: `${Math.max(20, point.red_count / 45)}px` }} />
                      <span>{shortDate(point.trade_date)}</span>
                    </div>
                  ))}
                </div>
                <div className="cycle-strip">
                  {cycles.slice(-6).map((point) => (
                    <button key={point.trade_date} onClick={() => setActivePage("data")} type="button">{cycleText(point.tag)}</button>
                  ))}
                </div>
              </div>
              <RiskPanel currentCycle={currentCycle} currentGateState={currentGateState} />
              <LedgerPanel tradeCount={tradeCount} winRate={winRate} />
            </section>
            <PatternAndTicket patterns={patterns} setActivePage={setActivePage} />
          </>
        )}

        {activePage === "tomorrow" && <TomorrowPage plan={tomorrowPlan} />}
        {activePage === "intraday" && <IntradayPage scan={intradayScan} onRefresh={refreshLiveData} />}
        {activePage === "live" && <LiveAlertsPage status={alertStatus} tracked={trackedSignals} onRefresh={refreshLiveData} />}
        {activePage === "strategy" && <StrategyPage patterns={patterns} experiments={experiments} onRefreshData={refreshData} />}
        {activePage === "backtest" && <BacktestPage backtest={backtest} energyBacktest={energyBacktest} shortEnergyBacktest={shortEnergyBacktest} experiments={experiments} feeModel={feeModel} />}
        {activePage === "risk" && <RiskPage riskCheck={riskCheck} currentCycle={currentCycle} rejectedCount={backtest?.rejected_count ?? 0} />}
        {activePage === "data" && <DataPage cycles={cycles} source={backtest?.source} />}
        {activePage === "ledger" && <LedgerPage backtest={backtest} />}
      </section>
    </main>
  );
}

function IndustryResearchPage() {
  const [data, setData] = useState<IndustryResearchResponse>({ page: 1, page_size: 20, total: 0, total_pages: 0, items: [], warning: "" });
  const [stats, setStats] = useState<IndustryResearchStats>({ total: 0, today_count: 0, source_count: 0, latest_published_at: null, latest_crawled_at: null, warning: "" });
  const [sources, setSources] = useState<IndustryResearchSource[]>([]);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [symbol, setSymbol] = useState("");
  const [reportType, setReportType] = useState("");
  const [source, setSource] = useState("");
  const [industry, setIndustry] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const pageSize = 20;

  const loadResearch = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
        report_type: reportType,
        source,
        industry,
        symbol,
        keyword,
      });
      const [itemsResponse, statsResponse, sourcesResponse] = await Promise.all([
        fetch(`${API_BASE}/api/industry-research?${params.toString()}`),
        fetch(`${API_BASE}/api/industry-research/stats`),
        fetch(`${API_BASE}/api/industry-research/sources`),
      ]);
      if (!itemsResponse.ok || !statsResponse.ok || !sourcesResponse.ok) throw new Error("产业研报接口异常");
      const itemsPayload: IndustryResearchResponse = await itemsResponse.json();
      const statsPayload: IndustryResearchStats = await statsResponse.json();
      const sourcesPayload: IndustryResearchSourcesResponse = await sourcesResponse.json();
      setData(itemsPayload);
      setStats(statsPayload);
      setSources(sourcesPayload.sources);
    } catch {
      setData((current) => ({ ...current, warning: "产业研报接口读取失败，请检查后端和 MySQL。" }));
    } finally {
      setLoading(false);
    }
  }, [industry, keyword, page, reportType, source, symbol]);

  useEffect(() => {
    void loadResearch();
  }, [loadResearch]);

  const resetAndSearch = () => {
    setPage(1);
    void loadResearch();
  };

  const triggerSync = async () => {
    setSyncing(true);
    try {
      const response = await fetch(`${API_BASE}/api/industry-research/sync?force=true`);
      if (!response.ok) throw new Error("同步失败");
      setPage(1);
      await loadResearch();
    } finally {
      setSyncing(false);
    }
  };

  const sourceOptions = sources.map((item) => item.name);
  const industryOptions = Array.from(new Set(data.items.map((item) => item.industry).filter(Boolean))).slice(0, 20);
  const reportTypes = ["产业报告", "个股拆解", "策略报告", "宏观研究", "券商晨会", "财务模型", "授权导入"];

  return (
    <section className="research-page">
      <div className="terminal-panel research-hero">
        <div className="panel-head">
          <span>产业研究数据库</span>
          <b>{loading ? "读取中" : `共 ${stats.total} 条`}</b>
        </div>
        <div className="research-hero-body">
          <div>
            <small>最新材料</small>
            <strong>{stats.total}</strong>
            <span>公开研报元数据、授权导入材料和后续自定义来源统一入库，按时间倒序分页。</span>
          </div>
          <button className="primary" onClick={triggerSync} type="button"><RefreshCw size={16} /> {syncing ? "同步中" : "同步研报"}</button>
        </div>
        <div className="research-stats">
          <span><b>{stats.today_count}</b>今日入库</span>
          <span><b>{stats.source_count}</b>数据来源</span>
          <span><b>{formatDateTime(stats.latest_published_at).slice(0, 10)}</b>最新发布</span>
          <span><b>{formatDateTime(stats.latest_crawled_at).slice(0, 10)}</b>最近同步</span>
        </div>
        {(data.warning || stats.warning) && <div className="calendar-warning">{data.warning || stats.warning}</div>}
      </div>

      <div className="terminal-panel research-filter-panel">
        <div className="research-filter-grid">
          <label>
            <span>关键词</span>
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="半导体、机器人、CPO..." />
          </label>
          <label>
            <span>股票</span>
            <input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="300750 或 宁德时代" />
          </label>
          <label>
            <span>类型</span>
            <select value={reportType} onChange={(event) => { setReportType(event.target.value); setPage(1); }}>
              <option value="">全部类型</option>
              {reportTypes.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <span>来源</span>
            <select value={source} onChange={(event) => { setSource(event.target.value); setPage(1); }}>
              <option value="">全部来源</option>
              {sourceOptions.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label>
            <span>行业</span>
            <select value={industry} onChange={(event) => { setIndustry(event.target.value); setPage(1); }}>
              <option value="">全部行业</option>
              {industryOptions.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <button onClick={resetAndSearch} type="button"><Search size={16} /> 检索</button>
        </div>
      </div>

      <div className="research-layout">
        <section className="research-list">
          {data.items.map((item) => (
            <article className="terminal-panel research-card" key={item.id}>
              <div className="research-card-top">
                <span>{item.report_type}</span>
                <b>{formatDateTime(item.published_at)}</b>
              </div>
              <h2>{item.title}</h2>
              <p>{item.summary || "暂无摘要，后续可通过授权文件导入全文或模型拆解。"}</p>
              <div className="research-tags">
                {item.institution && <span>{item.institution}</span>}
                {item.industry && <span>{item.industry}</span>}
                {item.author && <span>{item.author}</span>}
                {item.symbols.map((value) => <span key={value}>{value}</span>)}
                {item.tags.slice(0, 4).map((value) => <span key={value}>{value}</span>)}
              </div>
              <div className="research-meta">
                <span><FileText size={14} /> {item.source_type} · {item.source_name}</span>
                {item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer">查看来源</a> : <span>无来源链接</span>}
              </div>
            </article>
          ))}
          {!data.items.length && (
            <div className="terminal-panel research-empty">
              <FileText size={22} />
              <strong>暂无产业研报数据</strong>
              <span>点击“同步研报”拉取公开来源；授权材料可放入 `INDUSTRY_RESEARCH_IMPORT_DIR` 后入库。</span>
            </div>
          )}
          <div className="research-pagination">
            <button disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))} type="button"><ChevronLeft size={16} /> 上一页</button>
            <span>第 {data.page || page} / {data.total_pages || 1} 页 · {data.total} 条</span>
            <button disabled={data.total_pages === 0 || page >= data.total_pages} onClick={() => setPage((value) => value + 1)} type="button">下一页 <ChevronRight size={16} /></button>
          </div>
        </section>

        <aside className="terminal-panel research-source-panel">
          <div className="panel-head"><span>来源状态</span><b>{sources.length} 个</b></div>
          <div className="research-source-list">
            {sources.map((item) => (
              <div key={item.name}>
                <strong>{item.name}</strong>
                <span>{item.source_type} · {item.last_status || "pending"}</span>
                <small>{formatDateTime(item.last_sync_at)}</small>
                {item.last_error ? <em>{item.last_error}</em> : null}
              </div>
            ))}
            {!sources.length ? <p>首次同步后会显示来源状态。</p> : null}
          </div>
          <div className="theme-stack compact-themes">
            <div><strong>公开来源</strong><span>只采公开元数据和摘要，不绕过权限抓取全文。</span></div>
            <div><strong>授权导入</strong><span>买方模型、电话会议纪要和个股拆解可通过本地目录入库。</span></div>
          </div>
        </aside>
      </div>
    </section>
  );
}

function RiskPanel({ currentCycle, currentGateState }: { currentCycle?: CycleState; currentGateState: string }) {
  return (
    <div className="terminal-panel gates">
      <div className="panel-head">
        <span>风控闸门</span>
        <b className={currentGateState === "通过" ? "positive" : "negative"}>{currentGateState}</b>
      </div>
      <div className="gate-row"><span>当前周期</span><b>{cycleText(currentCycle?.tag)}</b></div>
      <div className="gate-row"><span>MA3 / MA5</span><b>{currentCycle ? `${currentCycle.ma3} / ${currentCycle.ma5}` : "-"}</b></div>
      <div className="gate-row"><span>容量成交额门槛</span><b className="positive">启用</b></div>
      <div className="gate-row"><span>连续亏损 2 笔禁买</span><b className="positive">监控</b></div>
      <div className="gate-row"><span>模式外交易</span><b className="negative">禁止</b></div>
    </div>
  );
}

function LedgerPanel({ tradeCount, winRate }: { tradeCount: number; winRate: number }) {
  return (
    <div className="terminal-panel ledger-panel">
      <div className="panel-head">
        <span>研究账本</span>
        <b>模型证据</b>
      </div>
      <div className="ledger-signal">
        <small>纪律指数</small>
        <strong>{tradeCount ? `${winRate.toFixed(1)}%` : "-"}</strong>
        <span>基于后端回测样本实时汇总</span>
      </div>
      <div className="ledger-mini-grid">
        <span><b>{tradeCount}</b>交易数</span>
        <span><b>{backtestLabel(winRate)}</b>胜率层级</span>
      </div>
    </div>
  );
}

function backtestLabel(winRate: number) {
  if (!winRate) return "-";
  if (winRate >= 55) return "强";
  if (winRate >= 45) return "稳";
  return "弱";
}

function InvestmentCalendarPage() {
  const fallbackCalendar: InvestmentCalendarResponse = {
    source: "前端备用数据",
    source_status: {},
    start_date: "2026-06-01",
    end_date: "2026-07-01",
    updated_at: "",
    event_count: investmentEvents.length,
    events: investmentEvents,
    warnings: ["后端投资日历接口暂不可用，当前显示备用事件清单。"],
  };
  const [calendarData, setCalendarData] = useState<InvestmentCalendarResponse | null>(null);
  const [calendarLoading, setCalendarLoading] = useState(true);
  const [calendarError, setCalendarError] = useState<string | null>(null);
  const data = calendarData ?? fallbackCalendar;
  const events = data.events;
  const groups = eventGroups(events);
  const eventMap = new Map(groups);
  const [selectedDate, setSelectedDate] = useState(todayKey());
  const selectedEvents = eventMap.get(selectedDate) ?? [];
  const highCount = events.filter((event) => event.impact === "high").length;
  const macroCount = events.filter((event) => ["宏观数据", "央行", "央行/利率", "利率", "流动性"].includes(event.category)).length;
  const aiCount = events.filter((event) => event.category.includes("科技") || event.category.includes("AI") || event.category.includes("半导体")).length;
  const nextHigh = events.find((event) => event.impact === "high");
  const sourceCount = Object.values(data.source_status).filter((status) => status.ok && status.count > 0).length;
  const updatedAt = data.updated_at ? new Date(data.updated_at).toLocaleString("zh-CN", { hour12: false }) : "未同步";

  useEffect(() => {
    let mounted = true;
    setCalendarLoading(true);
    fetch(`${API_BASE}/api/investment-calendar?days=30`)
      .then((response) => (response.ok ? response.json() : Promise.reject(response)))
      .then((payload: InvestmentCalendarResponse) => {
        if (!mounted) return;
        setCalendarData(payload);
        setCalendarError(null);
        const firstAvailable = payload.events.find((event) => event.date >= payload.start_date)?.date ?? payload.start_date;
        setSelectedDate((current) => (payload.events.some((event) => event.date === current) ? current : firstAvailable));
      })
      .catch(() => {
        if (!mounted) return;
        setCalendarError("投资日历接口读取失败，已切换备用清单。");
        setCalendarData(null);
        setSelectedDate(fallbackCalendar.start_date);
      })
      .finally(() => {
        if (mounted) setCalendarLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="calendar-page">
      <div className="terminal-panel calendar-hero">
        <div className="panel-head">
          <span>未来一个月事件雷达</span>
          <b>{data.start_date} 至 {data.end_date}</b>
        </div>
        <div className="calendar-hero-body">
          <div>
            <small>事件总数</small>
            <strong>{events.length}</strong>
            <span>{calendarLoading ? "正在同步财联社、同花顺、东方财富。" : `来源：${data.source} · 更新：${updatedAt}`}</span>
          </div>
          <div className="calendar-focus">
            <Clock3 size={18} />
            <span>{nextHigh ? `${nextHigh.date} · ${nextHigh.title}` : "暂无高影响事件"}</span>
          </div>
        </div>
        <div className="calendar-stats">
          <span><b>{highCount}</b>高影响</span>
          <span><b>{macroCount}</b>宏观/央行</span>
          <span><b>{aiCount}</b>科技/半导体</span>
          <span><b>{sourceCount || 1}</b>已接入源</span>
        </div>
        {(calendarError || data.warnings.length > 0) && (
          <div className="calendar-warning">{calendarError ?? data.warnings[0]}</div>
        )}
      </div>

      <div className="calendar-board-layout">
        <section className="terminal-panel calendar-board-panel">
          <div className="panel-head"><span>方块日历</span><b>点击日期查看完整事件</b></div>
          <div className="calendar-week-head">
            <span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span>
          </div>
          <div className="calendar-board">
            {calendarDates(data.start_date, data.end_date).map((date) => {
              const events = eventMap.get(date) ?? [];
              const topEvents = events.slice(0, 3);
              const highEvents = events.filter((event) => event.impact === "high").length;
              return (
                <button
                  className={selectedDate === date ? "calendar-cell active" : "calendar-cell"}
                  key={date}
                  onClick={() => setSelectedDate(date)}
                  type="button"
                >
                  <span className="cell-date">{date.slice(5)} <small>{weekdayText(date).replace("星期", "")}</small></span>
                  <span className="cell-count">{events.length ? `${events.length} 项` : "空窗"}</span>
                  <span className={highEvents ? "cell-impact hot" : "cell-impact"}>{highEvents ? `${highEvents} 高` : "观察"}</span>
                  <span className="cell-events">
                    {topEvents.map((event) => <em key={`${date}-${event.title}`}>{event.title}</em>)}
                    {events.length > topEvents.length ? <em>+{events.length - topEvents.length} 更多</em> : null}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <aside className="terminal-panel calendar-detail-panel">
          <div className="panel-head"><span>{selectedDate} · {weekdayText(selectedDate)}</span><b>{selectedEvents.length} 项事件</b></div>
          <div className="selected-event-list">
            {selectedEvents.map((event) => (
              <div className={`event-card impact-${event.impact}`} key={`${event.date}-${event.title}`}>
                <div className="event-card-head">
                  <span>{event.category}</span>
                  <b>{impactText(event.impact)}</b>
                </div>
                <h2>{event.title}</h2>
                <p>{event.detail}</p>
                <div className="event-meta">
                  <span><Globe2 size={13} /> {event.market}</span>
                  {event.source_url ? <a href={event.source_url} target="_blank" rel="noreferrer">{event.source}</a> : <span>{event.source}</span>}
                </div>
              </div>
            ))}
            {!selectedEvents.length ? <div className="empty-day">当日暂无重点事件，主要观察前后交易日催化延续。</div> : null}
          </div>

          <div className="theme-stack compact-themes">
            <div><strong>财联社</strong><span>投资日历事件、宏观数据和产业催化。</span></div>
            <div><strong>同花顺</strong><span>月度投资日历、概念与产业关联。</span></div>
            <div><strong>东方财富</strong><span>财经会议、个股日历、休市和新股提醒。</span></div>
          </div>
        </aside>
      </div>
    </section>
  );
}

function PatternAndTicket({ patterns, setActivePage }: { patterns: PatternRow[]; setActivePage: (page: PageId) => void }) {
  return (
    <section className="content-grid">
      <div className="terminal-panel wide">
        <div className="panel-head">
          <span>交易模式矩阵</span>
          <b>{patterns.filter((row) => row.state !== "LOCK").length} 个可用 / {patterns.filter((row) => row.state === "LOCK").length} 个锁定</b>
        </div>
        <div className="matrix-head">
          <span>模式</span><span>状态</span><span>仓位</span><span>期望</span><span>周期匹配</span>
        </div>
        {patterns.map((row) => (
          <button className="matrix-row row-button" key={row.name} onClick={() => setActivePage("strategy")} type="button">
            <span>{row.name}</span>
            <b className={stateClass(row.state)}>{stateText(row.state)}</b>
            <span>{row.size}</span>
            <span>{row.expectancy}</span>
            <span>{row.fit}</span>
          </button>
        ))}
      </div>

      <div className="ops-panel">
        <div className="panel-head">
          <span>模拟订单预检</span>
          <b className="warning">人工确认</b>
        </div>
        <div className="ticket">
          <label>候选标的</label>
          <strong>来自回测信号</strong>
          <label>触发模式</label>
          <strong>首板打板</strong>
          <label>计划仓位</label>
          <strong>6%</strong>
          <label>硬止损</label>
          <strong>-5.00%</strong>
        </div>
        <button className="full" onClick={() => setActivePage("risk")} type="button">查看模拟订单预检</button>
      </div>
    </section>
  );
}

function TomorrowPage({ plan }: { plan: TomorrowPlanResponse | null }) {
  const [activePreset, setActivePreset] = useState("conservative");
  const selected = plan?.plans.find((item) => item.id === activePreset) ?? plan?.plans[0] ?? null;

  return (
    <section className="tomorrow-page">
      <div className="terminal-panel tomorrow-brief">
        <div className="panel-head">
          <span>明日手动策略</span>
          <b>{plan ? `信号日 ${plan.decision_date} · 计划买入日 ${plan.planned_entry_date ?? "待确认"}` : "读取中"}</b>
        </div>
        <div className="tomorrow-summary">
          <div>
            <small>当前周期</small>
            <strong>{cycleText(plan?.cycle_tag)}</strong>
          </div>
          <div>
            <small>执行方式</small>
            <strong>手动确认</strong>
          </div>
          <div>
            <small>交易限制</small>
            <strong>非自动下单</strong>
          </div>
          <div>
            <small>策略版本</small>
            <strong>{plan?.strategy_version_generated_at ? "已接入" : "待生成"}</strong>
          </div>
        </div>
        <p className="manual-note">这里只给出下一交易日候选和开盘条件，不会连接券商，也不会发出任何真实订单。开盘不满足条件时应直接放弃。</p>
      </div>

      <div className="preset-tabs dark-tabs">
        {(plan?.plans ?? []).map((item) => (
          <button className={selected?.id === item.id ? "active" : ""} key={item.id} onClick={() => setActivePreset(item.id)} type="button">
            {item.name} · {item.version_eligible ? `${item.signals.length} 只` : "观察"}
          </button>
        ))}
      </div>

      <div className="terminal-panel">
        <div className="panel-head">
          <span>{selected?.name ?? "明日"}候选标的</span>
          <b>{selected?.version_id ?? "-"} · {selected?.version_verdict ?? "读取中"}</b>
        </div>
        {selected ? (
          <div className={selected.version_eligible ? "version-gate pass" : "version-gate watch"}>
            <strong>{selected.version_eligible ? "版本门槛通过" : "版本门槛未通过"}</strong>
            <span>{selected.version_reasons.join("；") || "等待策略版本库生成"}</span>
            <small>拒绝信号 {selected.rejected_count}</small>
          </div>
        ) : null}
        <div className="tomorrow-table">
          <span>标的</span><span>模式</span><span>收盘涨幅</span><span>成交额</span><span>排名</span><span>仓位</span><span>止损</span><span>买入原因</span><span>执行条件</span>
          {(selected?.signals ?? []).map((signal) => (
            <React.Fragment key={`${selected?.id}-${signal.symbol}-${signal.pattern}`}>
              <strong>{signal.name}<small>{signal.symbol}</small></strong>
              <span>{patternText(signal.pattern)}</span>
              <b className={pnlClass(signal.close_pct)}>{pct(signal.close_pct)}</b>
              <span>{signal.amount_billion.toFixed(2)} 亿</span>
              <span>{signal.sector_rank}</span>
              <span>{signal.planned_position_pct}%</span>
              <span>{pct(signal.stop_loss_pct)}</span>
              <span>{signal.reason}</span>
              <span>{signal.execution_rule}</span>
            </React.Fragment>
          ))}
        </div>
        {selected && !selected.signals.length ? <div className="sample-empty">当前维度没有明日候选，建议空仓观察。</div> : null}
      </div>
    </section>
  );
}

function IntradayPage({ scan, onRefresh }: { scan: IntradayScanResponse | null; onRefresh: () => Promise<void> }) {
  const [actionText, setActionText] = useState("等待扫描");
  const [busy, setBusy] = useState(false);

  async function scanNow(sendAlert: boolean) {
    setBusy(true);
    setActionText(sendAlert ? "正在扫描并同步飞书" : "正在扫描");
    try {
      const response = await fetch(`${API_BASE}${sendAlert ? "/api/intraday/sync-alerts" : "/api/intraday/scan"}`);
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      await onRefresh();
      if (sendAlert) {
        setActionText(`同步完成：新增 ${data.sync?.new_count ?? 0} 条，发送 ${data.sync?.sent_count ?? 0} 条`);
      } else {
        setActionText(`扫描完成：${data.signal_count ?? 0} 个买点`);
      }
    } catch (err) {
      setActionText(err instanceof Error ? err.message : "盘中扫描失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="intraday-page">
      <div className="terminal-panel intraday-brief">
        <div className="panel-head">
          <span>盘中实时买点</span>
          <b className={scan?.status.ready ? "positive" : "warning"}>{scan?.status.message ?? "读取中"}</b>
        </div>
        <div className="live-summary">
          <div>
            <small>行情源</small>
            <strong>{scan?.status.provider ?? "-"}</strong>
            <span>{scan?.status.realtime ? "实时行情" : "未接入实时行情"}</span>
          </div>
          <div>
            <small>扫描周期</small>
            <strong>{scan?.status.poll_seconds ?? "-"} 秒</strong>
            <span>后台开启后按此频率轮询</span>
          </div>
          <div>
            <small>当前买点</small>
            <strong>{scan?.signal_count ?? 0} 个</strong>
            <span>{scan?.scanned_at ?? "尚未扫描"}</span>
          </div>
        </div>
        <div className="live-actions">
          <button disabled={busy} onClick={() => scanNow(false)} type="button"><Radar size={16} /> 扫描一次</button>
          <button disabled={busy || !scan?.status.ready} onClick={() => scanNow(true)} type="button"><BellRing size={16} /> 扫描并飞书提醒</button>
        </div>
        <p className="manual-note">{actionText}。盘中雷达只做提醒，不会自动下单；实时行情未接入时不会生成实盘买点。</p>
      </div>

      <div className="terminal-panel">
        <div className="panel-head">
          <span>盘中触发列表</span>
          <b>{cycleText(scan?.cycle_tag ?? undefined)}</b>
        </div>
        <div className="intraday-table">
          <span>标的</span><span>触发</span><span>涨幅</span><span>价格</span><span>成交额</span><span>排名</span><span>仓位</span><span>执行策略</span>
          {(scan?.signals ?? []).map((signal) => (
            <React.Fragment key={signal.id}>
              <strong>{signal.name}<small>{signal.symbol}</small></strong>
              <span>{intradayPatternText(signal.pattern)}<small>{signal.trigger}</small></span>
              <b className={pnlClass(signal.pct)}>{pct(signal.pct)}</b>
              <span>{price(signal.price)}</span>
              <span>{signal.amount_billion.toFixed(2)} 亿</span>
              <span>{signal.sector_rank}</span>
              <span>{signal.planned_position_pct}% / {pct(signal.stop_loss_pct)}</span>
              <span>{signal.execution_rule}</span>
            </React.Fragment>
          ))}
        </div>
        {scan && !scan.signals.length ? <div className="sample-empty">当前没有盘中买点。若行情源未接入，这是正常状态。</div> : null}
      </div>
    </section>
  );
}

function LiveAlertsPage({
  status,
  tracked,
  onRefresh,
}: {
  status: AlertStatus | null;
  tracked: TrackedSignalsResponse | null;
  onRefresh: () => Promise<void>;
}) {
  const [actionText, setActionText] = useState("等待操作");
  const [busy, setBusy] = useState(false);

  async function runAction(url: string, doneText: string) {
    setBusy(true);
    setActionText("执行中");
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      await onRefresh();
      setActionText(`${doneText}：${data.sent_count ?? data.sync?.sent_count ?? 0} 条消息`);
    } catch (err) {
      setActionText(err instanceof Error ? err.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="live-page">
      <div className="terminal-panel live-brief">
        <div className="panel-head">
          <span>飞书提醒与 QMT 准备</span>
          <b>{status?.feishu.configured ? "通道已配置" : "等待配置"}</b>
        </div>
        <div className="live-summary">
          <div>
            <small>飞书群</small>
            <strong className={status?.feishu.enabled && status.feishu.configured ? "positive" : "warning"}>
              {status?.feishu.enabled && status.feishu.configured ? "已启用" : "未启用"}
            </strong>
            <span>{status?.feishu.chat_id || "未读取"}</span>
          </div>
          <div>
            <small>QMT 状态</small>
            <strong>{status?.qmt.mode ?? "模拟准备"}</strong>
            <span>{status?.qmt.broker ?? "兴业证券"} · 不会真实下单</span>
          </div>
          <div>
            <small>跟踪池</small>
            <strong>{tracked?.active_count ?? 0} 只</strong>
            <span>已结束 {tracked?.closed_count ?? 0} 只</span>
          </div>
        </div>
        <div className="live-actions">
          <button disabled={busy} onClick={() => runAction(`${API_BASE}/api/alerts/sync-tomorrow`, "同步完成")} type="button">
            <BellRing size={16} /> 同步并提醒明日信号
          </button>
          <button disabled={busy} onClick={() => runAction(`${API_BASE}/api/alerts/test-feishu`, "测试完成")} type="button">
            测试飞书
          </button>
          <button disabled={busy} onClick={() => onRefresh().then(() => setActionText("已刷新跟踪状态"))} type="button">
            刷新跟踪
          </button>
        </div>
        <p className="manual-note">{actionText}</p>
      </div>

      <div className="terminal-panel">
        <div className="panel-head">
          <span>信号跟踪</span>
          <b>止盈 {tracked?.tracks.filter((item) => item.status === "take_profit").length ?? 0} · 止损 {tracked?.tracks.filter((item) => item.status === "stop_loss").length ?? 0}</b>
        </div>
        <div className="tracked-table">
          <span>标的</span><span>状态</span><span>策略</span><span>参考价</span><span>最新价</span><span>收益</span><span>风控线</span><span>执行策略</span>
          {(tracked?.tracks ?? []).map((track) => (
            <React.Fragment key={track.id}>
              <strong>{track.name}<small>{track.symbol}</small></strong>
              <span>{trackStatusText(track.status)}</span>
              <span>{track.preset_name}<small>{track.version_id}</small></span>
              <span>{price(track.reference_price)}</span>
              <span>{price(track.last_price)}</span>
              <b className={pnlClass(track.last_pnl_pct)}>{pct(track.last_pnl_pct)}</b>
              <span>止损 {pct(track.stop_loss_pct)} / 止盈 {pct(track.take_profit_pct)}</span>
              <span>{track.exit_reason || track.execution_rule}</span>
            </React.Fragment>
          ))}
        </div>
        {tracked && !tracked.tracks.length ? <div className="sample-empty">暂无跟踪信号。出现明日候选后，点击同步或开启后台监控即可写入。</div> : null}
      </div>
    </section>
  );
}

function StrategyPage({
  patterns,
  experiments,
  onRefreshData,
}: {
  patterns: PatternRow[];
  experiments: StrategyExperimentsResponse | null;
  onRefreshData: () => Promise<void>;
}) {
  const [optimization, setOptimization] = useState<StrategyOptimizationResponse | null>(null);
  const [versions, setVersions] = useState<StrategyVersionsResponse | null>(null);
  const [optimizing, setOptimizing] = useState(false);
  const [buildingVersions, setBuildingVersions] = useState(false);
  const [optError, setOptError] = useState<string | null>(null);
  const best = experiments?.experiments.reduce<StrategyExperiment | null>((leader, item) => {
    if (!leader) return item;
    return (item.metrics.total_return_pct ?? -999) > (leader.metrics.total_return_pct ?? -999) ? item : leader;
  }, null);

  async function runOptimization() {
    setOptimizing(true);
    setOptError(null);
    try {
      const response = await fetch(`${API_BASE}/api/strategy-optimization`);
      if (!response.ok) throw new Error(await response.text());
      setOptimization(await response.json());
    } catch (err) {
      setOptError(err instanceof Error ? err.message : "自优化请求失败");
    } finally {
      setOptimizing(false);
    }
  }

  async function buildVersions() {
    setBuildingVersions(true);
    setOptError(null);
    try {
      const response = await fetch(`${API_BASE}/api/strategy-versions`);
      if (!response.ok) throw new Error(await response.text());
      setVersions(await response.json());
      await onRefreshData();
    } catch (err) {
      setOptError(err instanceof Error ? err.message : "版本库生成失败");
    } finally {
      setBuildingVersions(false);
    }
  }

  return (
    <section className="strategy-lab">
      <div className="terminal-panel lab-head">
        <div className="panel-head"><span>策略实验室</span><b>{experiments ? `最近一年 ${experiments.range_days} 个交易日` : "读取中"}</b></div>
        <div className="lab-summary">
          <div>
            <small>当前建议观察</small>
            <strong>{best?.name ?? "-"}</strong>
            <span>以总收益为临时排序依据，下一步应加入分市场、月份、回撤恢复天数和滑点压力测试。</span>
          </div>
          <div>
            <small>股票池限制</small>
            <strong>主板 + 创业板</strong>
            <span>排除科创板、北交所、ST；首板定义按 A 股涨跌停规则近似。</span>
          </div>
        </div>
      </div>

      <div className="experiment-grid">
        {(experiments?.experiments ?? []).map((item) => (
          <article className="experiment-card" key={item.id}>
            <div className="experiment-title">
              <div>
                <small>{item.id}</small>
                <h2>{item.name}</h2>
              </div>
              <b className={item.trade_count >= 20 ? "positive" : item.trade_count >= 5 ? "warning" : "negative"}>{item.trade_count} 笔</b>
            </div>
            <p>{item.description}</p>
            {item.settings.research_only ? <div className="risk-badge">研究模式 · 单票满仓 · 不建议实盘</div> : null}
            <div className="experiment-metrics">
              <span><b>{pct(item.metrics.total_return_pct)}</b>总收益</span>
              <span><b>{pct(item.metrics.win_rate_pct)}</b>胜率</span>
              <span><b>{pct(item.metrics.max_drawdown_pct)}</b>最大回撤</span>
              <span><b>{item.metrics.profit_loss_ratio?.toFixed(2) ?? "-"}</b>盈亏比</span>
            </div>
            <div className="setting-strip">
              <span>首板：{modeText(item.settings.first_limit_mode)}</span>
              <span>成交额 ≥ {item.settings.amount_min_billion} 亿</span>
              <span>强度排名 ≤ {item.settings.rank_limit}</span>
              <span>次日开盘 ≥ {item.settings.one_to_two_open_min_pct}%</span>
              {item.settings.position_pct ? <span>单票仓位：{item.settings.position_pct}%</span> : null}
              <span>周期过滤：{item.settings.cycle_filter ? "启用" : "放宽"}</span>
              <span>拒绝信号：{item.rejected_count}</span>
            </div>
            <div className="sample-trades">
              <div className="sample-head"><span>样本交易</span><span>模式</span><span>收益</span></div>
              {item.sample_trades.length ? item.sample_trades.map((trade) => (
                <div className="sample-row" key={`${item.id}-${trade.symbol}-${trade.entry_date}-${trade.pattern}`}>
                  <span>{trade.entry_date} · {trade.name}</span>
                  <span>{patternText(trade.pattern)}</span>
                  <b className={pnlClass(trade.pnl_pct)}>{pct(trade.pnl_pct)}</b>
                </div>
              )) : <div className="sample-empty">暂无成交样本</div>}
            </div>
          </article>
        ))}
      </div>

      <section className="terminal-panel mode-panel">
        <div className="panel-head"><span>原始模式状态</span><b>用于对照，不直接代表实验参数</b></div>
        <div className="strategy-grid compact">
          {patterns.map((pattern) => (
            <div className="strategy-card" key={pattern.name}>
              <h2>{pattern.name}</h2>
              <p>状态：<b className={stateClass(pattern.state)}>{stateText(pattern.state)}</b></p>
              <p>计划仓位：{pattern.size}</p>
              <p>期望值：{pattern.expectancy}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="terminal-panel reflection-panel">
        <div className="panel-head"><span>交易反思</span><b>基于已完成回测交易自动生成</b></div>
        <div className="reflection-grid">
          {(experiments?.experiments ?? []).map((item) => (
            <article className="reflection-card" key={`reflection-${item.id}`}>
              <div className="reflection-title">
                <div>
                  <small>{item.name}</small>
                  <h2>{item.reflection.verdict}</h2>
                </div>
                <b>{item.reflection.confidence}</b>
              </div>
              <ReflectionList title="优势" rows={item.reflection.strengths} />
              <ReflectionList title="问题" rows={item.reflection.weaknesses} />
              <ReflectionList title="下一轮优化" rows={item.reflection.suggestions} />
            </article>
          ))}
        </div>
      </section>

      <section className="terminal-panel optimization-panel">
        <div className="panel-head">
          <span>策略自优化</span>
          <button onClick={runOptimization} type="button">{optimizing ? "优化中" : "运行调参回测"}</button>
        </div>
        {optError && <div className="error-banner">{optError}</div>}
        <div className="optimization-grid">
          {(optimization?.groups ?? []).map((group) => (
            <article className="optimization-card" key={group.base_id}>
              <h2>{group.base_name}</h2>
              {group.candidates.map((candidate) => (
                <div className="optimization-row" key={candidate.id}>
                  <div>
                    <strong>{candidate.id.replace(`${group.base_id}-`, "")}</strong>
                    <span>成交额 {candidate.settings.amount_min_billion} 亿 · 排名 {candidate.settings.rank_limit} · 开盘 {candidate.settings.one_to_two_open_min_pct}%</span>
                  </div>
                  <b>{candidate.score.toFixed(2)}</b>
                  <span>{pct(candidate.metrics.total_return_pct)} / 回撤 {pct(candidate.metrics.max_drawdown_pct)}</span>
                  <em>{candidate.reflection.verdict}</em>
                </div>
              ))}
            </article>
          ))}
        </div>
        {!optimization && <p className="manual-note">点击后会围绕每个策略做“基准、收紧、放宽”三组净费用回测，再按收益和回撤综合排序。</p>}
      </section>

      <section className="terminal-panel version-panel">
        <div className="panel-head">
          <span>策略版本库</span>
          <button onClick={buildVersions} type="button">{buildingVersions ? "生成中" : "生成版本库"}</button>
        </div>
        {versions && (
          <div className="version-segments">
            <span>训练：{versions.segments.train.start} 至 {versions.segments.train.end}</span>
            <span>验证：{versions.segments.validation.start} 至 {versions.segments.validation.end}</span>
            <span>观察：{versions.segments.recent.start} 至 {versions.segments.recent.end}</span>
          </div>
        )}
        <div className="version-grid">
          {(versions?.groups ?? []).map((group) => (
            <article className="version-card" key={group.base_id}>
              <h2>{group.base_name}</h2>
              {group.recommended_version && (
                <div className={group.recommended_version.eligible ? "version-verdict pass" : "version-verdict watch"}>
                  <strong>{group.recommended_version.verdict}</strong>
                  <span>{group.recommended_version.version_id.replace(`${group.base_id}-`, "")}</span>
                </div>
              )}
              {group.versions.map((version) => (
                <div className="version-row" key={version.version_id}>
                  <div>
                    <strong>{version.version_id.replace(`${group.base_id}-`, "")}</strong>
                    <span>验证 {pct(version.validation.total_return_pct)} / 回撤 {pct(version.validation.max_drawdown_pct)} / {version.validation.trade_count} 笔</span>
                    <em>{version.reasons[0]}</em>
                  </div>
                  <b>{version.score.toFixed(2)}</b>
                </div>
              ))}
            </article>
          ))}
        </div>
        {!versions && <p className="manual-note">版本库会把最近一年切成训练段、验证段、最近观察段。验证段不赚钱或回撤超标的版本不会进入明日策略候选。</p>}
      </section>
    </section>
  );
}

function ReflectionList({ title, rows }: { title: string; rows: string[] }) {
  return (
    <div className="reflection-list">
      <h3>{title}</h3>
      {rows.map((row) => (
        <p key={`${title}-${row}`}>{row}</p>
      ))}
    </div>
  );
}

function BacktestPage({
  backtest,
  energyBacktest,
  shortEnergyBacktest,
  experiments,
  feeModel,
}: {
  backtest: BacktestResponse | null;
  energyBacktest: EnergyBacktestResponse | null;
  shortEnergyBacktest: StrategyBacktestResponse | null;
  experiments: StrategyExperimentsResponse | null;
  feeModel: FeeModel | null;
}) {
  const [activePreset, setActivePreset] = useState("conservative");
  const selected = experiments?.experiments.find((item) => item.id === activePreset) ?? experiments?.experiments[0] ?? null;
  const rows = selected?.trades ?? [];
  const coverageDays = backtest?.recent_market_days ?? experiments?.recent_market_days ?? [];
  const lastCompletedDate = backtest?.last_completed_entry_date ?? experiments?.last_completed_entry_date ?? "-";

  return (
    <section className="report-grid single">
      <div className="paper-card">
        <div className="report-headline">
          <div>
            <h2>回测摘要</h2>
            <p>行情最新交易日：{backtest?.latest_date ?? "读取中"}；最后可完整回测开仓日：{lastCompletedDate}；样本区间 {backtest?.range_days ?? "-"} 个交易日。</p>
          </div>
          <div className="preset-tabs">
            {(experiments?.experiments ?? []).map((item) => (
              <button className={selected?.id === item.id ? "active" : ""} key={item.id} onClick={() => setActivePreset(item.id)} type="button">
                {item.name}
              </button>
            ))}
          </div>
        </div>
        <div className="metrics">
          <span><b>{selected?.trade_count ?? 0}</b> 交易数</span>
          <span><b>{pct(selected?.metrics.total_return_pct)}</b> 总收益</span>
          <span><b>{pct(selected?.metrics.win_rate_pct)}</b> 胜率</span>
          <span><b>{pct(selected?.metrics.max_drawdown_pct)}</b> 最大回撤</span>
          <span><b>{selected?.metrics.profit_loss_ratio?.toFixed(2) ?? "-"}</b> 盈亏比</span>
          <span><b>{selected?.rejected_count ?? 0}</b> 拒绝信号</span>
        </div>
        <div className="coverage-note">{backtest?.completion_note ?? experiments?.completion_note ?? "交易明细仅统计已具备完整退出行情的样本。"}</div>
        <div className="market-coverage-grid">
          {coverageDays.map((day) => (
            <div className="market-day-tile" key={day.trade_date}>
              <div className="tile-date">{shortDate(day.trade_date)}</div>
              <strong>{day.red_count}</strong>
              <span>上涨 / 下跌 {day.down_count}</span>
              <small>涨停 {day.limit_up_count} · 跌停 {day.limit_down_count}</small>
              <small>沪深量能 {day.turnover_billion.toFixed(0)} 亿</small>
            </div>
          ))}
        </div>
        {feeModel && (
          <div className="fee-strip">
            <span>费用样本：{feeModel.sample_count} 笔 A 股交割</span>
            <span>最低佣金：{feeModel.min_commission.toFixed(2)} 元</span>
            <span>印花税：{(feeModel.stamp_tax_rate * 10000).toFixed(2)} / 万</span>
            <span>沪市过户费：{(feeModel.transfer_fee_rate * 10000).toFixed(2)} / 万</span>
            <span>佣金率上界：{(feeModel.commission_rate_upper_bound * 10000).toFixed(2)} / 万</span>
          </div>
        )}
      </div>

      <div className="paper-card energy-card">
        <div className="report-headline">
          <div>
            <h2>{energyBacktest?.strategy.name ?? "能量策略专项样本"}</h2>
            <p>{energyBacktest?.strategy.description ?? "近20日至少2次长上影试探60日线失败后，放量收盘站上60日线，次日开盘买入。"}</p>
          </div>
          <span className="pill">{energyBacktest ? `样本 ${energyBacktest.trades.length} 笔` : "读取中"}</span>
        </div>
        <div className="metrics energy-metrics">
          <span><b>{energyBacktest?.metrics.trade_count ?? 0}</b> 交易数</span>
          <span><b>{pct(energyBacktest?.metrics.total_return_pct)}</b> 总收益</span>
          <span><b>{pct(energyBacktest?.metrics.win_rate_pct)}</b> 胜率</span>
          <span><b>{pct(energyBacktest?.metrics.max_drawdown_pct)}</b> 最大回撤</span>
          <span><b>{energyBacktest?.metrics.profit_loss_ratio?.toFixed(2) ?? "-"}</b> 盈亏比</span>
          <span><b>{energyBacktest?.rejected_count ?? 0}</b> 拒绝信号</span>
        </div>
        {energyBacktest && (
          <div className="energy-samples">
            {[...energyBacktest.trades].slice(-5).reverse().map((trade) => (
              <div className="energy-sample" key={`energy-${trade.symbol}-${trade.signal_date}-${trade.entry_date}`}>
                <span>{trade.entry_date}</span>
                <b>{trade.name}</b>
                <small>{trade.symbol}</small>
                <strong className={pnlClass(trade.pnl_pct)}>{pct(trade.pnl_pct)}</strong>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="paper-card energy-card short-energy-card">
        <div className="report-headline">
          <div>
            <h2>{shortEnergyBacktest?.strategy.name ?? "超短能量交易专项样本"}</h2>
            <p>{shortEnergyBacktest?.strategy.description ?? "按市场能量、个股能量、前排/龙头分和买入模式筛选主线前排、低位补涨与新题材点火机会。"}</p>
          </div>
          <span className="pill">{shortEnergyBacktest ? `样本 ${shortEnergyBacktest.trades.length} 笔` : "读取中"}</span>
        </div>
        <div className="metrics energy-metrics">
          <span><b>{shortEnergyBacktest?.metrics.trade_count ?? 0}</b> 交易数</span>
          <span><b>{pct(shortEnergyBacktest?.metrics.total_return_pct)}</b> 总收益</span>
          <span><b>{pct(shortEnergyBacktest?.metrics.win_rate_pct)}</b> 胜率</span>
          <span><b>{pct(shortEnergyBacktest?.metrics.max_drawdown_pct)}</b> 最大回撤</span>
          <span><b>{shortEnergyBacktest?.metrics.profit_loss_ratio?.toFixed(2) ?? "-"}</b> 盈亏比</span>
          <span><b>{shortEnergyBacktest?.rejected_count ?? 0}</b> 拒绝信号</span>
        </div>
        {shortEnergyBacktest && (
          <div className="energy-samples">
            {[...shortEnergyBacktest.trades].slice(-5).reverse().map((trade) => (
              <div className="energy-sample" key={`short-energy-${trade.symbol}-${trade.signal_date}-${trade.entry_date}`}>
                <span>{trade.entry_date}</span>
                <b>{trade.name}</b>
                <small>{trade.symbol}</small>
                <strong className={pnlClass(trade.pnl_pct)}>{pct(trade.pnl_pct)}</strong>
              </div>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <div className="paper-card quality-card">
          <h2>策略质量拆解</h2>
          <div className="quality-grid">
            <QualityTable title="按模式" rows={selected.quality.by_pattern} label={(value) => patternText(value)} />
            <QualityTable title="按月份" rows={selected.quality.by_month} />
            <QualityTable title="按板块" rows={selected.quality.by_board} />
          </div>
        </div>
      )}

      <div className="paper-card">
        <div className="report-headline">
          <div>
            <h2>{selected?.name ?? "实验维度"}交易明细</h2>
            <p>按开仓日期倒序展示，红色为盈利，绿色为亏损。</p>
          </div>
        </div>
        <div className="trade-row table-head">
          <span>信号日期</span>
          <span>开仓日期</span>
          <span>清仓日期</span>
          <span>股票名称</span>
          <span>A股代码</span>
          <span>模式</span>
          <span>周期</span>
          <span>开仓价</span>
          <span>清仓价</span>
          <span>信号依据</span>
          <span>仓位</span>
          <span>毛收益</span>
          <span>费用</span>
          <span>收益率</span>
          <span>清仓原因</span>
          <span>卖后 3 日</span>
        </div>
        {[...rows].reverse().map((trade) => (
          <div className="trade-row" key={`${trade.symbol}-${trade.signal_date}-${trade.entry_date}-${trade.pattern}`}>
            <span>{trade.signal_date}</span>
            <span>{trade.entry_date}</span>
            <span>{trade.exit_date}</span>
            <span>{trade.name}</span>
            <span>{trade.symbol}</span>
            <span>{patternText(trade.pattern)}</span>
            <span>{cycleText(trade.cycle_tag)}</span>
            <span>{price(trade.entry_price)}</span>
            <span>{price(trade.exit_price)}</span>
            <span>{trade.signal_reason}</span>
            <span>{trade.position_pct}%</span>
            <span>{pct(trade.gross_pnl_pct)}</span>
            <span>{trade.fee_amount ? `${trade.fee_amount.toFixed(2)}元 / ${pct(trade.fee_pct)}` : "-"}</span>
            <b className={pnlClass(trade.pnl_pct)}>{pct(trade.pnl_pct)}</b>
            <span>{trade.exit_reason}</span>
            <span>{pct(trade.after_3d_return_pct)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function QualityTable({ title, rows, label }: { title: string; rows: QualityRow[]; label?: (value: string) => string }) {
  return (
    <div className="quality-table">
      <h3>{title}</h3>
      <div className="quality-row table-head">
        <span>维度</span><span>交易数</span><span>总收益</span><span>胜率</span><span>最大回撤</span>
      </div>
      {rows.map((row) => (
        <div className="quality-row" key={`${title}-${row.key}`}>
          <span>{label ? label(row.key) : row.key}</span>
          <span>{row.metrics.trade_count ?? 0}</span>
          <b className={pnlClass(row.metrics.total_return_pct ?? 0)}>{pct(row.metrics.total_return_pct)}</b>
          <span>{pct(row.metrics.win_rate_pct)}</span>
          <span>{pct(row.metrics.max_drawdown_pct)}</span>
        </div>
      ))}
    </div>
  );
}

function RiskPage({ riskCheck, currentCycle, rejectedCount }: { riskCheck: string; currentCycle?: CycleState; rejectedCount: number }) {
  return (
    <section className="content-grid">
      <div className="terminal-panel">
        <div className="panel-head"><span>风控预检结果</span><b className="positive">仅模拟</b></div>
        <p className="large-status">{riskCheck}</p>
        <div className="gate-row"><span>周期</span><b>{cycleText(currentCycle?.tag)}</b></div>
        <div className="gate-row"><span>被拒绝信号</span><b className={rejectedCount ? "warning" : "positive"}>{rejectedCount}</b></div>
        <div className="gate-row"><span>交易网关</span><b className="negative">未连接</b></div>
      </div>
      <div className="ops-panel">
        <div className="panel-head"><span>实盘保护</span><b className="negative">已锁定</b></div>
        <p>当前版本不会发出任何真实订单。后续接入券商前，所有订单必须经过周期、容量、仓位、止损、连续亏损和模式外交易闸门。</p>
      </div>
    </section>
  );
}

function DataPage({ cycles, source }: { cycles: CycleState[]; source?: string }) {
  const rows = [...cycles].reverse();
  return (
    <section className="terminal-panel">
      <div className="panel-head"><span>行情数据缓存</span><b>{sourceText(source)} · 最近一个月 {cycles.length} 个交易日</b></div>
      <MarketLineChart cycles={cycles} />
      <div className="data-table">
        <span>日期</span><span>上涨</span><span>下跌</span><span>涨停</span><span>跌停</span><span>成交额</span><span>沪市</span><span>深市</span><span>MA5</span><span>周期标签</span>
        {rows.map((cycle) => (
          <React.Fragment key={cycle.trade_date}>
            <span>{cycle.trade_date}</span>
            <span>{cycle.red_count}</span>
            <span>{cycle.down_count}</span>
            <span>{cycle.limit_up_count}</span>
            <span>{cycle.limit_down_count}</span>
            <span>{formatBillion(cycle.turnover_billion)}</span>
            <span>{formatBillion(cycle.sh_turnover_billion)}</span>
            <span>{formatBillion(cycle.sz_turnover_billion)}</span>
            <span>{cycle.ma5}</span>
            <b>{cycleText(cycle.tag)}</b>
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}

function MarketLineChart({ cycles }: { cycles: CycleState[] }) {
  if (!cycles.length) return null;
  const width = 920;
  const height = 220;
  const padding = 28;
  const maxValue = Math.max(1, ...cycles.flatMap((cycle) => [cycle.red_count, cycle.limit_up_count * 25, cycle.limit_down_count * 25]));
  const x = (index: number) => padding + (index * (width - padding * 2)) / Math.max(1, cycles.length - 1);
  const y = (value: number) => height - padding - (value / maxValue) * (height - padding * 2);
  const line = (values: number[]) => values.map((value, index) => `${x(index)},${y(value)}`).join(" ");
  const latest = cycles[cycles.length - 1];

  return (
    <div className="market-line-card">
      <div className="market-chart-head">
        <span>市场宽度走势</span>
        <b>{latest.trade_date} · 上涨 {latest.red_count} · 下跌 {latest.down_count} · 涨停 {latest.limit_up_count} · 跌停 {latest.limit_down_count} · 成交额 {formatBillion(latest.turnover_billion)}</b>
      </div>
      <svg className="market-line-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="最近一个月市场宽度折线图">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="chart-axis" />
        <polyline points={line(cycles.map((cycle) => cycle.red_count))} className="line-red-count" />
        <polyline points={line(cycles.map((cycle) => cycle.limit_up_count * 25))} className="line-limit-up" />
        <polyline points={line(cycles.map((cycle) => cycle.limit_down_count * 25))} className="line-limit-down" />
        {cycles.map((cycle, index) => (
          <g key={cycle.trade_date}>
            <circle cx={x(index)} cy={y(cycle.red_count)} r="3" className="dot-red-count" />
            {index % 4 === 0 || index === cycles.length - 1 ? <text x={x(index)} y={height - 8} textAnchor="middle">{shortDate(cycle.trade_date)}</text> : null}
          </g>
        ))}
      </svg>
      <div className="market-legend"><span className="legend-red">上涨家数</span><span className="legend-up">涨停数 x25</span><span className="legend-down">跌停数 x25</span></div>
    </div>
  );
}
function LedgerPage({ backtest }: { backtest: BacktestResponse | null }) {
  return (
    <section className="ledger-page">
      <div className="terminal-panel ledger-overview">
        <div className="panel-head"><span>研究账本</span><b>月度校准雏形</b></div>
        <div className="ledger-overview-body">
          <div>
            <small>本轮模型结论</small>
            <h2>{sourceText(backtest?.source)}</h2>
            <p>股票池只包含沪深主板和创业板，排除科创板、北交所、ST。当前版本用于规则链路和近似回测验证，盘口级打板回测需要后续接入更细行情。</p>
          </div>
          <div className="ledger-status">
            <span>研究模式</span>
            <strong>模拟运行</strong>
          </div>
        </div>
      </div>

      <div className="ledger-metrics">
        <span><b>{backtest?.metrics.trade_count ?? 0}</b>交易数</span>
        <span><b>{pct(backtest?.metrics.average_return_pct)}</b>平均收益</span>
        <span><b>{pct(backtest?.metrics.win_rate_pct)}</b>胜率</span>
        <span><b>{backtest?.rejected_count ?? 0}</b>风控拒绝</span>
      </div>

      <div className="ledger-grid">
        <article className="terminal-panel ledger-card">
          <div className="panel-head"><span>执行纪律</span><b>硬约束</b></div>
          <p>模式外交易禁止；连续亏损触发禁买；容量成交额门槛启用；所有实盘动作仍需人工确认。</p>
        </article>
        <article className="terminal-panel ledger-card">
          <div className="panel-head"><span>复盘入口</span><b>日 / 周 / 月</b></div>
          <p>后续可把日复盘、周复盘、月复盘模板接入这里，形成行情、信号、交易和纪律的闭环。</p>
        </article>
        <article className="terminal-panel ledger-card">
          <div className="panel-head"><span>下一步校准</span><b>数据质量</b></div>
          <p>重点补盘口级成交、竞价金额、封单强度和实际成交滑点，减少日线近似回测偏差。</p>
        </article>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);



