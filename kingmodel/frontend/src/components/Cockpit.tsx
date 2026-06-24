import { AlertTriangle, Ban, BrainCircuit, Check, ChevronRight, CircleX, Clock3, Database, Eye, Radio, ShieldAlert, Target, TrendingDown, TrendingUp, Zap } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import type { DashboardData } from "../types";
import { FlowMap } from "./FlowMap";
import { ScoreGauge } from "./ScoreGauge";

function Panel({ title, kicker, source, children, className = "" }: { title: string; kicker?: string; source?: string; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><header><div>{kicker ? <span>{kicker}</span> : null}<h2>{title}</h2></div><div className="panel-meta">{source ? <small>{source}</small> : null}<ChevronRight size={15} /></div></header>{children}</section>;
}

function qualitySource(data: DashboardData, key: string) {
  return data.data_quality?.[key]?.source ?? data.meta.source;
}

function CoreGroups({ cores }: { cores: DashboardData["cores"] }) {
  const kinds = ["连板情绪核心", "趋势容量核心", "创业板20cm弹性核心"];
  return <div className="core-groups">{kinds.map((kind) => {
    const items = cores.filter((core) => core.kind === kind);
    return <details key={kind} open><summary><span>{kind}</span><b>{items.length}</b></summary><div className="core-list">{items.length ? items.map((core, index) => <article key={`${kind}-${core.code}`}><div className="core-rank">{String(index + 1).padStart(2, "0")}</div><div className="core-identity"><strong>{core.name}<small>{core.code}</small></strong><p>{core.evidence}</p></div><div className="core-score"><b>{core.score}</b><em className={core.change >= 0 ? "up" : "down"}>{core.change >= 0 ? "+" : ""}{core.change.toFixed(2)}%</em></div></article>) : <p className="group-empty">当前可信快照暂无符合条件的标的</p>}</div></details>;
  })}</div>;
}

function Ladder({ items }: { items: DashboardData["ladder"] }) {
  const heights = [...new Set(items.map((item) => item.height))].sort((a, b) => b - a);
  if (!items.length) return <div className="ladder-empty"><Database size={23} /><span>连板查询未通过校验，等待下一次可信快照</span></div>;
  return <div className="ladder-groups">{heights.map((height) => <section key={height}><header><strong>{height}板</strong><span>{items.filter((item) => item.height === height).length}只</span></header><div className="ladder-list">{items.filter((item) => item.height === height).map((item) => <article key={item.code}>
    <div className="ladder-stock"><span>{item.factor_type}</span><strong>{item.name}<small>{item.code}</small></strong><div className="ladder-counts"><b>连续{item.height}板</b><small>近{item.recent_window_days ?? 5}日 {item.recent_limit_count ?? item.height}板</small></div><em className="up">+{item.change.toFixed(2)}%</em></div>
    <div className="concept-tags">{item.concepts.map((concept) => <span key={concept}>{concept}</span>)}</div>
    <div className="primary-factor"><Zap size={14} /><p><b>第一性因素</b>{item.primary_factor}</p><span className={`confidence confidence-${item.confidence}`}>{item.confidence}置信</span></div>
    <details><summary>证据摘要 · {item.source}</summary><p>{item.evidence}</p></details>
  </article>)}</div></section>)}</div>;
}

function PlannedTargets({ items }: { items: DashboardData["planned_targets"] }) {
  if (!items.length) return <div className="plan-empty"><Target size={24} /><div><strong>当前没有达到执行门槛的计划标的</strong><span>系统不会用弱标的补足数量，等待市场许可与核心评分改善。</span></div></div>;
  return <div className="plan-grid">{items.map((item, index) => <article key={item.code}>
    <header><span className={`plan-priority priority-${item.priority}`}>{item.priority}</span><div><small>{String(index + 1).padStart(2, "0")} · {item.kind}</small><strong>{item.name}<b>{item.code}</b></strong></div><em>{item.score.toFixed(1)}</em></header>
    <p className="plan-logic">{item.logic}</p>
    {item.setup ? <div className="plan-condition observe"><Target size={15} /><span><b>买点类型</b>{item.setup}</span></div> : null}
    {item.payoff ? <div className="plan-condition observe"><TrendingUp size={15} /><span><b>盈亏比/胜率</b>{item.payoff}</span></div> : null}
    <div className="plan-condition observe"><Eye size={15} /><span><b>次日观察</b>{item.observation}</span></div>
    <div className="plan-condition invalid"><CircleX size={15} /><span><b>失效条件</b>{item.invalidation}</span></div>
    {item.risk_note ? <div className="plan-condition invalid"><ShieldAlert size={15} /><span><b>风险约束</b>{item.risk_note}</span></div> : null}
    <footer><span>{item.holding_period}</span><small>{item.source} · {item.confidence}置信</small></footer>
  </article>)}</div>;
}

const SHADOW_METRICS = [
  ["calibrated_probability", "概率"], ["expectancy_payoff", "期望"], ["mainline_core", "主线"],
  ["style_cycle_match", "适配"], ["tradeability", "交易"], ["data_model_reliability", "可靠"],
] as const;

function ShadowTop3({ shadow, featureDays = 0 }: { shadow: DashboardData["ml_shadow"]; featureDays?: number }) {
  if (!shadow) return null;
  return <Panel title="模型影子 Top3" kicker="SHADOW RANKING · 暂不执行" className="shadow-panel">
    <div className="shadow-status"><BrainCircuit size={17} /><div><strong>规则基线正在积累走步样本</strong><span>{shadow.reason}</span></div><em>{featureDays} 个特征日</em></div>
    {shadow.plans.length ? <div className="shadow-grid">{shadow.plans.map((item) => <article key={item.code}>
      <header><span>#{item.rank}</span><div><small>{item.kind}</small><strong>{item.name}<b>{item.code}</b></strong></div><em>{item.score}<i>分</i></em></header>
      <div className="shadow-metrics">{SHADOW_METRICS.map(([key, label]) => <div key={key}><span>{label}</span><b>{item.score_breakdown[key]}</b></div>)}<div className="risk"><span>扣分</span><b>-{item.score_breakdown.risk_penalty}</b></div></div>
      <p>{item.blocked_reason}</p><footer><span>{item.holding_period}</span><small>仅记录结果，不进入正式计划</small></footer>
    </article>)}</div> : <div className="shadow-empty"><ShieldAlert size={20} /><span>{shadow.reason}</span></div>}
  </Panel>;
}

export function Cockpit({ data }: { data: DashboardData }) {
  const upRatio = Math.round(data.breadth.up / Math.max(1, data.breadth.eligible) * 100);
  return <div className="cockpit-grid">
    <section className="permission-card">
      <div className="permission-top"><span className="live-tag"><Radio size={13} /> DECISION</span><span>仓位上限</span></div>
      <div className="permission-main"><div><small>市场许可</small><h1>{data.permission.label}</h1></div><strong>{data.permission.position_limit}<i>%</i></strong></div>
      <div className="permission-rule allow"><Check size={16} /><span><small>允许模式</small>{data.permission.allowed}</span></div>
      <div className="permission-rule deny"><Ban size={16} /><span><small>禁止模式</small>{data.permission.forbidden}</span></div>
    </section>

    <Panel title="状态矩阵" kicker="MARKET STATE" className="scores-panel">
      <div className="cycle-line"><span>{data.state.cycle}</span><em>{data.state.structure}</em></div>
      <div className="score-row"><ScoreGauge label="赚钱 M" value={data.state.money} tone="red" /><ScoreGauge label="亏钱 L" value={data.state.loss} tone="green" /><ScoreGauge label="趋势 T" value={data.state.trend} tone="blue" /><ScoreGauge label="投机 S" value={data.state.speculation} tone="amber" /></div>
    </Panel>

    <Panel title="市场广度" kicker="BREADTH · 全A含科创/北交" source={qualitySource(data, "breadth")} className="breadth-panel">
      <div className="breadth-split"><div className="breadth-visual" style={{ "--up": `${upRatio}%` } as CSSProperties}><span>{upRatio}%</span><small>上涨占比</small></div><div className="breadth-numbers"><div><TrendingUp size={15} /><span>上涨</span><strong>{data.breadth.up}</strong></div><div><TrendingDown size={15} /><span>下跌</span><strong>{data.breadth.down}</strong></div><div><span>平盘</span><strong>{data.breadth.flat}</strong></div><div><span>中位数</span><strong className={data.breadth.median >= 0 ? "up" : "down"}>{data.breadth.median.toFixed(2)}%</strong></div></div></div>
      <div className="limit-strip"><span>涨停 <b>{data.breadth.limit_up}</b></span><span>跌停 <b>{data.breadth.limit_down}</b></span><span>炸板 <b>{data.breadth.failed_limit}</b></span><span>可交易连板 <b>{data.breadth.continuous}</b></span></div>
    </Panel>

    <Panel title="资金迁移图谱" kicker="CAPITAL FLOW" className="flow-panel"><FlowMap data={data} /></Panel>

    <Panel title="板块反馈对照" kicker="POSITIVE / NEGATIVE" className="feedback-panel">
      <div className="feedback-compare"><section className="positive-zones"><header><div><span>POSITIVE</span><strong>正反馈板块</strong></div><em>{data.mainlines.length}</em></header>{data.mainlines.map((item) => <article key={item.name}><div><b>{item.name}</b><small>{item.role}</small></div><strong>+{item.change.toFixed(2)}%</strong><i style={{ width: `${Math.min(100, Math.abs(item.change) * 14)}%` }} /></article>)}</section>
      <section className="loss-zones"><header><div><span>NEGATIVE</span><strong>负反馈板块</strong></div><em>{data.negative.length}</em></header>{data.negative.map((item) => <article key={item.name}><div><b>{item.name}</b><small>{item.severity === "high" ? "高风险" : "扩散观察"}</small></div><strong>{item.change.toFixed(2)}%</strong><i style={{ width: `${Math.min(100, Math.abs(item.change) * 14)}%` }} /></article>)}</section></div>
    </Panel>

    <Panel title="实时风险与容量反馈" kicker="LIVE RISK · NO STATIC COPY" source={data.capacity.source} className="alerts-panel">
      <div className="capacity-strip"><div><small>成交额样本</small><strong>TOP {data.capacity.sample}</strong></div><div><small>上涨 / 下跌</small><strong><i className="up">{data.capacity.up}</i> / <i className="down">{data.capacity.down}</i></strong></div><div><small>中位涨跌幅</small><strong className={data.capacity.median >= 0 ? "up" : "down"}>{data.capacity.median >= 0 ? "+" : ""}{data.capacity.median.toFixed(2)}%</strong></div><div><small>容量判断</small><strong>{data.capacity.label}</strong></div></div>
      <div className="alert-stack">{data.alerts.map((alert) => <div className={`alert-item ${alert.level}`} key={alert.title}><AlertTriangle size={15} /><span><strong>{alert.title}</strong><small>{alert.detail}</small></span></div>)}</div>
    </Panel>

    <Panel title="明日计划标的" kicker="EXECUTION WATCHLIST · 只列达标核心" className="plans-panel"><PlannedTargets items={data.planned_targets} /></Panel>

    <ShadowTop3 shadow={data.ml_shadow} featureDays={data.feature_store_status?.feature_days} />

    <Panel title="核心梯队" kicker="ALL QUALIFIED CORES · 排除科创/北交" className="cores-panel"><CoreGroups cores={data.cores} /></Panel>

    <Panel title="当日连板梯队" kicker="LIMIT-UP LADDER · FIRST-PRINCIPLE FACTOR" source={qualitySource(data, "continuous")} className="ladder-panel"><Ladder items={data.ladder} /></Panel>

    <Panel title="盘中确认清单" kicker="CHECKPOINTS" className="checkpoints-panel">
      <ol>{data.checkpoints.map((item, index) => <li key={item}><span>{index + 1}</span>{item}</li>)}</ol>
      <div className="next-check"><Clock3 size={14} />下一次图谱更新取决于数据层新鲜度</div>
    </Panel>

    <Panel title="隔夜预期" kicker="SENTIMENT" className="sentiment-panel">
      <div className="sentiment-mini">{data.sentiment.map((item) => <article key={item.topic}><div><Target size={15} /><strong>{item.topic}</strong><em>热度 {item.heat}</em></div><p>{item.catalyst}</p><footer><span>拥挤度 {item.crowding}</span><span>验证：{item.validation}</span></footer></article>)}</div>
      <p className="sentiment-policy"><ShieldAlert size={14} />舆情只提示预期与拥挤，不直接改变评分和仓位。</p>
    </Panel>
  </div>;
}
