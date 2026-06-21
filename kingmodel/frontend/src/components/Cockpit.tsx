import { AlertTriangle, Ban, Check, ChevronRight, Clock3, Radio, ShieldAlert, Target, TrendingDown, TrendingUp } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import type { DashboardData } from "../types";
import { FlowMap } from "./FlowMap";
import { ScoreGauge } from "./ScoreGauge";

function Panel({ title, kicker, children, className = "" }: { title: string; kicker?: string; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><header><div>{kicker ? <span>{kicker}</span> : null}<h2>{title}</h2></div><ChevronRight size={15} /></header>{children}</section>;
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

    <Panel title="实时风险" kicker="RISK FEED" className="alerts-panel">
      <div className="alert-stack">{data.alerts.map((alert) => <div className={`alert-item ${alert.level}`} key={alert.title}><AlertTriangle size={15} /><span><strong>{alert.title}</strong><small>{alert.detail}</small></span></div>)}</div>
    </Panel>

    <Panel title="资金迁移图谱" kicker="CAPITAL FLOW" className="flow-panel"><FlowMap data={data} /></Panel>

    <Panel title="市场广度" kicker="BREADTH" className="breadth-panel">
      <div className="breadth-split"><div className="breadth-visual" style={{ "--up": `${upRatio}%` } as CSSProperties}><span>{upRatio}%</span><small>上涨占比</small></div><div className="breadth-numbers"><div><TrendingUp size={15} /><span>上涨</span><strong>{data.breadth.up}</strong></div><div><TrendingDown size={15} /><span>下跌</span><strong>{data.breadth.down}</strong></div><div><span>中位数</span><strong className="down">{data.breadth.median.toFixed(2)}%</strong></div></div></div>
      <div className="limit-strip"><span>涨停 <b>{data.breadth.limit_up}</b></span><span>跌停 <b>{data.breadth.limit_down}</b></span><span>炸板 <b>{data.breadth.failed_limit}</b></span><span>连板 <b>{data.breadth.continuous}</b></span></div>
    </Panel>

    <Panel title="核心梯队" kicker="CORE HIERARCHY" className="cores-panel">
      <div className="core-list">{data.cores.map((core, index) => <article key={core.code}><div className="core-rank">0{index + 1}</div><div className="core-identity"><span>{core.kind}</span><strong>{core.name}<small>{core.code}</small></strong><p>{core.evidence}</p></div><div className="core-score"><b>{core.score}</b><em className={core.change >= 0 ? "up" : "down"}>{core.change >= 0 ? "+" : ""}{core.change.toFixed(2)}%</em></div></article>)}</div>
    </Panel>

    <Panel title="负反馈坐标" kicker="LOSS ZONES" className="negative-panel">
      <div className="negative-grid">{data.negative.map((item) => <div key={item.name}><span>{item.name}</span><strong>{item.change.toFixed(2)}%</strong><i style={{ width: `${Math.min(100, Math.abs(item.change) * 14)}%` }} /></div>)}</div>
    </Panel>

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
