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

function signedPct(value: number) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
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

function PlanBullets({ title, items, tone = "observe" }: { title: string; items?: string[]; tone?: "observe" | "invalid" }) {
  if (!items?.length) return null;
  return <div className={`plan-condition ${tone}`}><ChevronRight size={15} /><span><b>{title}</b><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></span></div>;
}

function SectorLinkage({ items = [] }: { items?: NonNullable<DashboardData["sector_linkage"]> }) {
  if (!items.length) return <div className="linkage-empty"><Zap size={22} /><span>暂无可验证的板块联动数据，计划标的不会因孤立强票获得加分。</span></div>;
  return <div className="linkage-grid">{items.slice(0, 6).map((item) => <article key={item.name} className={`linkage-${item.level}`}>
    <header><div><small>{item.level}</small><strong>{item.name}</strong></div><em>{item.score.toFixed(1)}</em></header>
    <div className="linkage-leader"><span>核心</span><b>{item.leader}<small>{item.leader_code}</small></b></div>
    <div className="linkage-metrics">
      <div><span>涨停</span><b>{item.limit_up_count}</b></div>
      <div><span>跟随</span><b>{item.follower_count}</b></div>
      <div><span>20cm</span><b>{item.elastic_count}</b></div>
      <div><span>梯队</span><b>{item.tier_count}</b></div>
      <div><span>大涨</span><b>{item.strong_count}</b></div>
      <div><span>板块涨跌</span><b className={item.median_change >= 0 ? "up" : "down"}>{signedPct(item.median_change)}</b></div>
    </div>
    <div className="linkage-evidence">{item.evidence.slice(0, 4).map((text) => <span key={text}>{text}</span>)}</div>
    {item.followers.length ? <div className="linkage-followers">{item.followers.slice(0, 4).map((follower) => <span key={follower.code}>{follower.name}<b>{follower.change.toFixed(1)}%</b></span>)}</div> : null}
    {item.risks.length ? <p>{item.risks.join("；")}</p> : <p>后排有扩散，暂未识别明显孤立风险。</p>}
  </article>)}</div>;
}

function CapacityCores({ items = [] }: { items?: NonNullable<DashboardData["capacity_cores"]> }) {
  if (!items.length) return <div className="linkage-empty"><Database size={22} /><span>暂无同日成交额核心数据；趋势容量模式不会强行补票。</span></div>;
  return <div className="capacity-core-list">{items.slice(0, 8).map((item, index) => <article key={item.code} className={!item.tradable ? "disabled" : ""}>
    <div className="capacity-rank"><b>#{index + 1}</b><small>成交额#{item.rank}</small></div>
    <div className="capacity-core-main">
      <header><strong>{item.name}<small>{item.code}</small></strong><em className={item.change >= 0 ? "up" : "down"}>{item.change >= 0 ? "+" : ""}{item.change.toFixed(2)}%</em></header>
      <p>{item.reason}</p>
      <footer>{item.tags.slice(0, 5).map((tag) => <span key={tag}>{tag}</span>)}</footer>
    </div>
    <div className="capacity-core-score"><b>{item.score.toFixed(1)}</b><small>{item.amount_label}</small></div>
  </article>)}</div>;
}

function NegativeStocks({ items = [] }: { items?: NonNullable<DashboardData["negative_stocks"]> }) {
  if (!items.length) return <div className="linkage-empty"><ShieldAlert size={22} /><span>暂无可验证的个股负反馈；风险仅按市场/板块层展示。</span></div>;
  return <div className="negative-stock-grid">{items.slice(0, 12).map((item) => <article key={item.code} className={`severity-${item.severity}`}>
    <header><div><small>{item.industry || "未分行业"}</small><strong>{item.name}<b>{item.code}</b></strong></div><em className={item.change >= 0 ? "up" : "down"}>{signedPct(item.change)}</em></header>
    <p>{item.reason}</p>
    <div className="negative-stock-metrics"><span>回撤 <b>{item.drawdown.toFixed(1)}%</b></span><span>成交 <b>{item.amount_label}</b></span></div>
    <footer>{item.tags.slice(0, 5).map((tag) => <span key={tag}>{tag}</span>)}</footer>
  </article>)}</div>;
}

function EventSignals({ items = [] }: { items?: NonNullable<DashboardData["event_signals"]> }) {
  if (!items.length) return <div className="linkage-empty"><ShieldAlert size={22} /><span>暂无可审计的隔夜舆情/盘后复盘信号；计划不会使用空数据加分。</span></div>;
  return <div className="event-signal-list">{items.slice(0, 6).map((item) => <article key={`${item.type}-${item.topic}`}>
    <header><div><small>{item.type === "overnight_sentiment" ? "隔夜舆情" : item.type === "post_market_review" ? "盘后复盘" : "模型复盘"}</small><strong>{item.topic}</strong></div><em>{item.score.toFixed(1)}</em></header>
    <p>{item.catalyst}</p>
    <div><span>验证：{item.validation}</span><span>风险：{item.risk}</span></div>
    <footer><b>{item.crowding}</b><small>{item.source}</small></footer>
  </article>)}</div>;
}

function DailyBrief({ brief }: { brief?: DashboardData["daily_brief"] }) {
  if (!brief?.text) return null;
  return <section className="daily-brief-card">
    <header><div><span>DAILY REVIEW · ≤300字</span><h2>盘面复盘总结</h2></div><small>{brief.source}</small></header>
    <div className="daily-brief-body">
      <p>{brief.text}</p>
      <aside>
        <span>明日观察标</span>
        {(brief.observations ?? []).length ? (brief.observations ?? []).map((item, index) => <article key={`${item.code ?? item.name}-${index}`}>
          <b>{item.name ?? "观察方向"}{item.code ? <small>{item.code}</small> : null}</b>
          <em>{item.type ?? "观察"}</em>
          <p>{item.reason ?? "等待盘面确认"}</p>
        </article>) : <article><b>暂无达标观察标</b><em>空仓条件</em><p>等待主线、广度和容量承接同步确认。</p></article>}
      </aside>
    </div>
  </section>;
}

function PlannedTargets({ items }: { items: DashboardData["planned_targets"] }) {
  if (!items.length) return <div className="plan-empty"><Target size={24} /><div><strong>当前没有达到执行门槛的计划标的</strong><span>系统不会用弱标的补足数量，等待市场许可与核心评分改善。</span></div></div>;
  return <div className="plan-grid">{items.map((item, index) => <article key={item.code}>
    <header><span className={`plan-priority priority-${item.priority}`}>{item.priority}</span><div><small>{String(index + 1).padStart(2, "0")} · {item.kind}</small><strong>{item.name}<b>{item.code}</b></strong></div><em>{item.score.toFixed(1)}</em></header>
    <p className="plan-logic">{item.logic}</p>
    {item.setup ? <div className="plan-condition observe"><Target size={15} /><span><b>买点类型</b>{item.setup}</span></div> : null}
    {item.payoff ? <div className="plan-condition observe"><TrendingUp size={15} /><span><b>盈亏比/胜率</b>{item.payoff}</span></div> : null}
    {item.sector_linkage_level ? <div className="plan-condition observe"><Zap size={15} /><span><b>板块联动</b>{item.sector_linkage_level} {typeof item.sector_linkage_score === "number" ? `${item.sector_linkage_score.toFixed(1)}分` : ""} · {item.leader_effect}</span></div> : null}
    <PlanBullets title="联动证据" items={item.sector_linkage_evidence} />
    {item.event_signal_score ? <div className="plan-condition observe"><Radio size={15} /><span><b>舆情/复盘</b>{item.event_signal_score.toFixed(1)}分 · 只作为预期差与次日验证条件，不替代盘面确认</span></div> : null}
    <PlanBullets title="舆情验证" items={item.event_signals?.map((signal) => `${signal.topic}：${signal.validation}`)} />
    <PlanBullets title="买入前提" items={item.entry_preconditions} />
    <PlanBullets title="触发买点" items={item.entry_trigger} />
    <PlanBullets title="禁买条件" items={item.no_buy_conditions} tone="invalid" />
    {item.position_plan ? <div className="plan-condition observe"><ShieldAlert size={15} /><span><b>仓位计划</b>{item.position_plan}</span></div> : null}
    <PlanBullets title="止损计划" items={item.stop_loss} tone="invalid" />
    <PlanBullets title="止盈计划" items={item.take_profit} />
    <PlanBullets title="卖出/持有" items={item.sell_plan} />
    <div className="plan-condition observe"><Eye size={15} /><span><b>次日观察</b>{item.observation}</span></div>
    <div className="plan-condition invalid"><CircleX size={15} /><span><b>失效条件</b>{item.invalidation}</span></div>
    {item.risk_note ? <div className="plan-condition invalid"><ShieldAlert size={15} /><span><b>风险约束</b>{item.risk_note}</span></div> : null}
    <footer><span>{item.holding_period}</span><small>{item.source} · {item.confidence}置信</small></footer>
  </article>)}</div>;
}

const ML_STAGE_LABEL: Record<string, { title: string; tone: string; detail: string }> = {
  rule_only: { title: "规则影子积累", tone: "cold", detail: "只记录规则影子样本，真实机器学习模型尚未参与决策。" },
  shadow_learning: { title: "影子学习中", tone: "warm", detail: "已达到首次训练区间，但仍以观察和校准为主。" },
  assisted: { title: "模型辅助观察", tone: "hot", detail: "模型可作为辅助权重，但仍需要人工和盘面确认。" },
  live_eligible: { title: "实盘参考候选", tone: "live", detail: "样本达到长期门槛，可进入更严格的实盘参考评估。" },
};

function formatMaybeDate(value?: string | null) {
  if (!value) return "暂无";
  return value.replace("T", " ").replace("+08:00", "").replace("+00:00", " UTC");
}

function percentMaybe(value: number | null | undefined) {
  if (typeof value !== "number") return "待回填";
  return `${(value * 100).toFixed(1)}%`;
}

function returnMaybe(value: number | null | undefined) {
  if (typeof value !== "number") return "待回填";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function gateProgress(days: number, gate: number) {
  return Math.max(0, Math.min(100, Math.round(days / gate * 100)));
}

function MLLearningProgress({ data }: { data: DashboardData }) {
  const feature = data.feature_store_status;
  const system = data.ml_system;
  const shadow = data.ml_shadow;
  const review = data.ml_review;
  if (!feature && !system && !shadow && !review) return null;
  const featureDays = feature?.feature_days ?? system?.feature_days ?? 0;
  const outcomeDays = feature?.outcome_days ?? system?.outcome_days ?? 0;
  const stageKey = system?.stage ?? "rule_only";
  const stage = ML_STAGE_LABEL[stageKey] ?? ML_STAGE_LABEL.rule_only;
  const championCount = system?.champion_count ?? 0;
  const challengerCount = system?.challenger_count ?? 0;
  const missingFirstTrain = Math.max(0, 20 - outcomeDays);
  const gates = [
    { label: "首次训练", days: 20, note: missingFirstTrain > 0 ? `还差 ${missingFirstTrain} 个结果交易日` : "可尝试训练" },
    { label: "辅助观察", days: 60, note: outcomeDays >= 60 ? "达到辅助观察门槛" : `还差 ${Math.max(0, 60 - outcomeDays)} 天` },
    { label: "实盘参考", days: 120, note: outcomeDays >= 120 ? "达到长期样本门槛" : `还差 ${Math.max(0, 120 - outcomeDays)} 天` },
  ];
  const modules = system?.modules ?? {};
  const latestPlans = shadow?.plans ?? [];
  const latestOutcomes = (review?.items ?? []).slice(0, 6);
  return <Panel title="机器学习进度" kicker="ML LEARNING STATUS · 不等于实盘推荐" className="ml-progress-panel">
    <div className="ml-progress-hero">
      <div className={`ml-stage ml-stage-${stage.tone}`}>
        <BrainCircuit size={22} />
        <span>当前阶段</span>
        <strong>{stage.title}</strong>
        <p>{stage.detail}</p>
      </div>
      <div className="ml-verdict">
        <small>模型是否参与正式计划</small>
        <strong>{championCount > 0 ? "已有模型可参与辅助评分" : "没有参与，当前仍是规则计划"}</strong>
        <p>{championCount > 0 ? `Champion ${championCount} 个，Challenger ${challengerCount} 个。` : "Champion=0，Challenger=0；影子 Top3 只用于积累样本，不应按机器学习推荐执行。"}</p>
      </div>
      <div className="ml-days">
        <article><span>特征交易日</span><b>{featureDays}</b><small>最新 {feature?.latest_trade_date ?? "暂无"}</small></article>
        <article><span>结果标签日</span><b>{outcomeDays}</b><small>训练主要看标签样本</small></article>
        <article><span>模型数量</span><b>{championCount + challengerCount}</b><small>Champion {championCount} / Challenger {challengerCount}</small></article>
      </div>
    </div>

    <div className="ml-gate-grid">
      {gates.map((gate) => <article key={gate.label}>
        <header><span>{gate.label}</span><b>{outcomeDays}/{gate.days}</b></header>
        <div className="ml-gate-bar"><i style={{ width: `${gateProgress(outcomeDays, gate.days)}%` }} /></div>
        <p>{gate.note}</p>
      </article>)}
    </div>

    <div className="ml-progress-body">
      <section className="ml-review-card">
        <header><span>结果回填</span><small>{review?.is_backtest === false ? "影子标签，不是实盘回测" : "样本统计"}</small></header>
        <div className="ml-review-grid">{(review?.summary ?? []).map((item) => <article key={item.horizon}>
          <b>{item.horizon}日</b>
          <span>样本 {item.samples}</span>
          <strong>{percentMaybe(item.win_rate)}</strong>
          <small>{returnMaybe(item.average_return)}</small>
        </article>)}</div>
        <p>{review?.notice ?? "暂无结果标签。样本不足时，胜率和平均收益只用于检查流程，不用于实盘判断。"}</p>
      </section>

      <section className="ml-shadow-card">
        <header><span>最新影子 Top3</span><small>{shadow?.plan_version ?? "暂无版本"}</small></header>
        <div>{latestPlans.length ? latestPlans.map((item) => <article key={item.code}>
          <b>#{item.rank} {item.name}<small>{item.code}</small></b>
          <em>{item.score}分</em>
          <p>{item.blocked_reason || "只记录样本，不进入正式计划。"}</p>
        </article>) : <article><b>暂无影子计划</b><p>等待收盘快照生成后写入。</p></article>}</div>
      </section>

      <section className="ml-training-card">
        <header><span>训练与模块</span><small>{system?.last_training_run?.version ?? "暂无训练"}</small></header>
        <dl>
          <div><dt>最近训练</dt><dd>{system?.last_training_run?.status ?? "暂无"}</dd></div>
          <div><dt>训练样本</dt><dd>{system?.last_training_run?.sample_count ?? 0}</dd></div>
          <div><dt>完成时间</dt><dd>{formatMaybeDate(system?.last_training_run?.finished_at)}</dd></div>
        </dl>
        <div className="ml-module-list">{Object.entries(modules).map(([name, status]) => <span key={name} className={`module-${status}`}>{name}<b>{status}</b></span>)}</div>
      </section>

      <section className="ml-outcome-card">
        <header><span>最近标签明细</span><small>最多显示 6 条</small></header>
        <div>{latestOutcomes.length ? latestOutcomes.map((item) => <article key={`${item.trade_date}-${item.code}-${item.horizon}`}>
          <b>{item.trade_date} {item.name}<small>{item.code}</small></b>
          <span>{item.horizon}日 / {item.tradable ? "可交易" : "不可交易"}</span>
          <em className={item.net_return >= 0 ? "up" : "down"}>{returnMaybe(item.net_return)}</em>
        </article>) : <article><b>暂无回填</b><span>后续交易日自动补齐 1/3/5/10 日标签。</span></article>}</div>
      </section>
    </div>
  </Panel>;
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
    <DailyBrief brief={data.daily_brief} />

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
      <div className="feedback-compare"><section className="positive-zones"><header><div><span>POSITIVE</span><strong>正反馈板块</strong></div><em>{data.mainlines.length}</em></header>{data.mainlines.map((item) => <article key={item.name}><div><b>{item.name}</b><small>{item.role}</small></div><strong className={item.change >= 0 ? "up" : "down"}>{signedPct(item.change)}</strong><i style={{ width: `${Math.min(100, Math.abs(item.change) * 14)}%` }} /></article>)}</section>
      <section className="loss-zones"><header><div><span>NEGATIVE</span><strong>负反馈板块</strong></div><em>{data.negative.length}</em></header>{data.negative.map((item) => <article key={item.name}><div><b>{item.name}</b><small>{item.severity === "high" ? "高风险" : "扩散观察"}</small></div><strong>{item.change.toFixed(2)}%</strong><i style={{ width: `${Math.min(100, Math.abs(item.change) * 14)}%` }} /></article>)}</section></div>
    </Panel>

    <Panel title="个股负反馈池" kicker="LOSS STOCKS · 跌停/炸板/大回撤" source={qualitySource(data, "negative_stocks")} className="negative-stocks-panel"><NegativeStocks items={data.negative_stocks} /></Panel>

    <Panel title="板块联动性" kicker="SECTOR LINKAGE · 龙头带动/后排扩散" source={qualitySource(data, "sector_linkage")} className="linkage-panel"><SectorLinkage items={data.sector_linkage} /></Panel>

    <Panel title="容量核心" kicker="CAPACITY CORES · 趋势/中军候选" source={qualitySource(data, "capacity_cores")} className="capacity-cores-panel"><CapacityCores items={data.capacity_cores} /></Panel>

    <Panel title="实时风险与容量反馈" kicker="LIVE RISK · NO STATIC COPY" source={data.capacity.source} className="alerts-panel">
      <div className="capacity-strip"><div><small>成交额样本</small><strong>TOP {data.capacity.sample}</strong></div><div><small>上涨 / 下跌</small><strong><i className="up">{data.capacity.up}</i> / <i className="down">{data.capacity.down}</i></strong></div><div><small>中位涨跌幅</small><strong className={data.capacity.median >= 0 ? "up" : "down"}>{data.capacity.median >= 0 ? "+" : ""}{data.capacity.median.toFixed(2)}%</strong></div><div><small>容量判断</small><strong>{data.capacity.label}</strong></div></div>
      <div className="alert-stack">{data.alerts.map((alert) => <div className={`alert-item ${alert.level}`} key={alert.title}><AlertTriangle size={15} /><span><strong>{alert.title}</strong><small>{alert.detail}</small></span></div>)}</div>
    </Panel>

    <Panel title="明日计划标的" kicker="EXECUTION WATCHLIST · 只列达标核心" className="plans-panel"><PlannedTargets items={data.planned_targets} /></Panel>

    <MLLearningProgress data={data} />

    <ShadowTop3 shadow={data.ml_shadow} featureDays={data.feature_store_status?.feature_days} />

    <Panel title="核心梯队" kicker="ALL QUALIFIED CORES · 排除科创/北交" className="cores-panel"><CoreGroups cores={data.cores} /></Panel>

    <Panel title="当日连板梯队" kicker="LIMIT-UP LADDER · FIRST-PRINCIPLE FACTOR" source={qualitySource(data, "continuous")} className="ladder-panel"><Ladder items={data.ladder} /></Panel>

    <Panel title="盘中确认清单" kicker="CHECKPOINTS" className="checkpoints-panel">
      <ol>{data.checkpoints.map((item, index) => <li key={item}><span>{index + 1}</span>{item}</li>)}</ol>
      <div className="next-check"><Clock3 size={14} />下一次图谱更新取决于数据层新鲜度</div>
    </Panel>

    <Panel title="隔夜预期" kicker="SENTIMENT" className="sentiment-panel">
      <EventSignals items={data.event_signals} />
      <p className="sentiment-policy"><ShieldAlert size={14} />舆情/复盘已进入计划评分，但只改变预期差和验证条件；盘面不确认时不得买入。</p>
    </Panel>
  </div>;
}
