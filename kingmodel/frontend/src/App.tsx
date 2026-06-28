import { useCallback, useEffect, useState } from "react";
import { Activity, Bell, BookOpenCheck, Boxes, ChevronDown, Clock3, Database, GitBranch, History, LayoutDashboard, LogOut, Menu, RefreshCw, ScanSearch, Settings, ShieldAlert, Target, X } from "lucide-react";
import { api } from "./api";
import { Cockpit } from "./components/Cockpit";
import { FlowMap } from "./components/FlowMap";
import { LoginPage } from "./components/LoginPage";
import { SettingsPage } from "./components/SettingsPage";
import type { DashboardData, HistoryItem, Workspace } from "./types";

const nav: Array<{ id: Workspace; label: string; icon: typeof Activity }> = [
  { id: "cockpit", label: "决策驾驶舱", icon: LayoutDashboard },
  { id: "map", label: "市场图谱", icon: GitBranch },
  { id: "sectors", label: "主线板块", icon: Boxes },
  { id: "cores", label: "核心标的", icon: Target },
  { id: "sentiment", label: "隔夜舆情", icon: ScanSearch },
  { id: "review", label: "影子跟踪", icon: BookOpenCheck },
  { id: "history", label: "历史验证", icon: History },
  { id: "settings", label: "系统设置", icon: Settings }
];

function MarketMapWorkspace({ data }: { data: DashboardData }) {
  const nodes = data.market_graph?.nodes ?? [];
  const edges = data.market_graph?.edges ?? [];
  return <div className="workspace-page">
    <div className="page-heading"><span>MARKET MAP</span><h1>市场图谱</h1><p>不是板块列表，而是把负反馈、市场状态、主线扩散、容量核心和明日计划放到一张关系图里。</p></div>
    <div className="map-shell"><FlowMap data={data} /></div>
    <div className="map-stats">
      <article><span>节点</span><strong>{nodes.length}</strong><p>市场、板块、核心、计划</p></article>
      <article><span>关系</span><strong>{edges.length}</strong><p>资金迁移与带动链路</p></article>
      <article><span>计划</span><strong>{data.planned_targets.length}</strong><p>允许少于3只或空仓</p></article>
    </div>
  </div>;
}

function SectorsWorkspace({ data }: { data: DashboardData }) {
  const linkageByName = new Map((data.sector_linkage ?? []).map((item) => [item.name, item]));
  return <div className="workspace-page">
    <div className="page-heading"><span>SECTOR DIAGNOSIS</span><h1>主线板块</h1><p>这里专门判断板块是不是主线、有没有后排扩散、有没有20cm弹性、是否存在孤立和断层。</p></div>
    <div className="sector-diagnosis">
      {data.mainlines.map((line, index) => {
        const linkage = linkageByName.get(line.name) ?? (data.sector_linkage ?? []).find((item) => item.name.includes(line.name) || line.name.includes(item.name));
        return <article key={line.name}>
          <header><div><small>{index === 0 ? "主线候选" : line.role}</small><strong>{line.name}</strong></div><em>{line.score}</em></header>
          <p>{line.flow}</p>
          <div className="sector-diagnosis-metrics">
            <span>涨停 <b>{linkage?.limit_up_count ?? "—"}</b></span>
            <span>后排 <b>{linkage?.follower_count ?? "—"}</b></span>
            <span>20cm <b>{linkage?.elastic_count ?? "—"}</b></span>
            <span>联动 <b>{linkage?.score?.toFixed(1) ?? "—"}</b></span>
            <span>板块涨跌 <b className={(linkage?.median_change ?? 0) >= 0 ? "up" : "down"}>{typeof linkage?.median_change === "number" ? `${linkage.median_change >= 0 ? "+" : ""}${linkage.median_change.toFixed(2)}%` : "—"}</b></span>
          </div>
          <footer>{line.tags.map((tag) => <span key={tag}>{tag}</span>)}{linkage?.risks?.map((risk) => <span className="risk" key={risk}>{risk}</span>)}</footer>
        </article>;
      })}
    </div>
  </div>;
}

function CoresWorkspace({ data }: { data: DashboardData }) {
  return <div className="workspace-page">
    <div className="page-heading"><span>CORE CANDIDATES</span><h1>核心标的</h1><p>核心地位来自主动性、容量承接、板块带动和可交易性，不等于静态涨幅排名。</p></div>
    <div className="capacity-core-list workspace-capacity">{(data.capacity_cores ?? []).slice(0, 12).map((item, index) => <article key={item.code} className={!item.tradable ? "disabled" : ""}>
      <div className="capacity-rank"><b>#{index + 1}</b><small>成交额#{item.rank}</small></div>
      <div className="capacity-core-main"><header><strong>{item.name}<small>{item.code}</small></strong><em className={item.change >= 0 ? "up" : "down"}>{item.change >= 0 ? "+" : ""}{item.change.toFixed(2)}%</em></header><p>{item.reason}</p><footer>{item.tags.map((tag) => <span key={tag}>{tag}</span>)}</footer></div>
      <div className="capacity-core-score"><b>{item.score.toFixed(1)}</b><small>{item.amount_label}</small></div>
    </article>)}</div>
    <div className="core-cards">{data.cores.map((core) => <article key={`${core.kind}-${core.code}`}><span>{core.kind}</span><h2>{core.name}<small>{core.code}</small></h2><strong>{core.score}</strong><p>{core.evidence}</p><button>已进入候选池</button></article>)}</div>
  </div>;
}

function SentimentWorkspace({ data }: { data: DashboardData }) {
  return <div className="workspace-page">
    <div className="page-heading"><span>OVERNIGHT / REVIEW SIGNALS</span><h1>隔夜舆情</h1><p>舆情和复盘只负责给出预期差、拥挤度和次日验证条件；盘面不确认时不能买入。</p></div>
    <div className="event-signal-list workspace-signals">{(data.event_signals ?? []).map((entry) => <article key={`${entry.type}-${entry.topic}`}>
      <header><div><small>{entry.type === "overnight_sentiment" ? "隔夜舆情" : entry.type === "post_market_review" ? "盘后复盘" : "模型复盘"}</small><strong>{entry.topic}</strong></div><em>{entry.score.toFixed(1)}</em></header>
      <p>{entry.catalyst}</p>
      <div><span>次日验证：{entry.validation}</span><span>风险：{entry.risk}</span></div>
      <footer><b>{entry.crowding}</b><small>{entry.source}</small></footer>
    </article>)}</div>
    {data.sentiment.length ? <div className="sentiment-board">{data.sentiment.map((entry) => <article key={entry.topic}><div className="heat">{entry.heat}</div><div><span>拥挤度 {entry.crowding}</span><h2>{entry.topic}</h2><p>{entry.catalyst}</p><footer>次日验证：{entry.validation}</footer></div></article>)}</div> : <div className="empty-workspace"><ScanSearch size={34} /><h2>暂无可验证隔夜舆情</h2><p>静态兜底话题已剔除；没有来源、时间和验证条件的数据不会参与交易计划。</p></div>}
  </div>;
}

function HistoryWorkspace({ items }: { items: HistoryItem[] }) {
  return <div className="workspace-page">
    <div className="page-heading"><span>SNAPSHOT HISTORY</span><h1>历史验证</h1><p>这里展示系统已保存的收盘快照，方便检查数据是否持续沉淀。</p></div>
    {items.length ? <div className="history-table"><header><span>时间</span><span>交易日</span><span>数据层</span><span>来源</span><span>类型</span></header>{items.map((item) => <div key={item.id}>
      <span>{new Date(item.created_at).toLocaleString("zh-CN", { hour12: false })}</span>
      <span>{item.trade_date}</span>
      <span className={item.freshness === "live" ? "up" : "down"}>{item.freshness}</span>
      <span>{item.source}</span>
      <span>{item.is_official ? "正式" : "临时"}</span>
    </div>)}</div> : <div className="empty-workspace"><History size={34} /><h2>暂无历史快照</h2><p>后端没有返回历史记录时才显示这里。</p></div>}
  </div>;
}

function ReviewWorkspace({ data }: { data: DashboardData }) {
  const review = data.ml_review;
  const pct = (value?: number | null) => typeof value === "number" ? `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%` : "—";
  const price = (value?: number | null) => typeof value === "number" ? value.toFixed(2) : "—";
  return <div className="workspace-page"><div className="page-heading"><span>SHADOW OUTCOME TRACKING</span><h1>影子计划跟踪</h1><p>这里不是实盘回测。当前只按统一标签回看计划：次日开盘买入、固定周期收盘退出，用于机器学习样本沉淀和规则校验。</p></div>
    <div className="review-warning"><ShieldAlert size={16} /><span>{review?.notice ?? "当前为影子计划收益标签，不是实盘回测；尚未模拟你的真实盘中买卖点、止损止盈和仓位。"}</span></div>
    <div className="review-summary">{(review?.summary ?? []).map((entry) => <article key={entry.horizon}><span>{entry.horizon}D</span><div><small>可成交样本</small><strong>{entry.samples}</strong></div><div><small>标签胜率</small><strong>{entry.win_rate === null ? "—" : `${(entry.win_rate * 100).toFixed(1)}%`}</strong></div><div><small>平均净收益</small><strong className={(entry.average_return ?? 0) >= 0 ? "up" : "down"}>{entry.average_return === null ? "—" : `${entry.average_return >= 0 ? "+" : ""}${(entry.average_return * 100).toFixed(2)}%`}</strong></div></article>)}</div>
    {review?.items.length ? <div className="review-table outcome-table"><header><span>计划 / 标的</span><span>入场</span><span>退出</span><span>收益</span><span>过程风险</span><span>标签规则</span><span>可成交</span></header>{review.items.slice(0, 60).map((entry) => <div key={`${entry.trade_date}-${entry.code}-${entry.horizon}`}>
      <span><b>{entry.name}</b><small>{entry.trade_date} · {entry.code} · 计划#{entry.rank ?? "—"}</small></span>
      <span><b>{entry.entry_trade_date ?? "—"}</b><small>开盘 {price(entry.entry_price)}</small></span>
      <span><b>{entry.exit_trade_date ?? "—"}</b><small>{entry.holding_days ?? entry.horizon}日收盘 {price(entry.exit_price)}</small></span>
      <span className={entry.net_return >= 0 ? "up" : "down"}><b>{entry.tradable ? pct(entry.net_return) : "—"}</b><small>毛收益 {pct(entry.gross_return)}</small></span>
      <span><b className="up">MFE {pct(entry.mfe)}</b><small className="down">MAE {pct(entry.mae)} · 盈亏比 {entry.payoff_ratio?.toFixed(2) ?? "—"}</small></span>
      <span><b>{entry.label_version ?? "—"}</b><small>{entry.entry_rule ?? "次日开盘统一打标"}；{entry.exit_rule ?? `${entry.horizon}日收盘退出`}</small></span>
      <span>{entry.tradable ? "是" : entry.blocked_reason ?? "否"}</span>
    </div>)}</div> : <div className="empty-workspace"><Database size={34} /><h2>等待未来收益标签</h2><p>影子计划会在后续交易日自动回填，不调用通达信。</p></div>}
  </div>;
}

function SecondaryWorkspace({ workspace, data, historyItems }: { workspace: Workspace; data: DashboardData; historyItems: HistoryItem[] }) {
  const item = nav.find((entry) => entry.id === workspace)!;
  if (workspace === "map") return <MarketMapWorkspace data={data} />;
  if (workspace === "sectors") return <SectorsWorkspace data={data} />;
  if (workspace === "cores") return <CoresWorkspace data={data} />;
  if (workspace === "sentiment") return <SentimentWorkspace data={data} />;
  if (workspace === "review") return <ReviewWorkspace data={data} />;
  if (workspace === "history") return <HistoryWorkspace items={historyItems} />;
  return <div className="workspace-page"><div className="page-heading"><span>WORKSPACE</span><h1>{item.label}</h1><p>该工作区已连接统一快照和认证结构，后续数据会随采集任务持续沉淀。</p></div><div className="empty-workspace"><Database size={34} /><h2>等待数据沉淀</h2><p>当前模式：{data.meta.freshness} · 来源：{data.meta.source}</p></div></div>;
}

export default function App() {
  const [username, setUsername] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [workspace, setWorkspace] = useState<Workspace>("cockpit");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const loadDashboard = useCallback(async () => {
    const dashboard = await api.dashboard();
    setData(dashboard);
  }, []);

  useEffect(() => {
    Promise.all([api.me(), api.dashboard()]).then(([user, dashboard]) => { setUsername(user.username); setData(dashboard); }).catch(() => setUsername(null)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!username) return;
    const timer = window.setInterval(() => loadDashboard().catch(() => undefined), 30_000);
    return () => window.clearInterval(timer);
  }, [loadDashboard, username]);

  useEffect(() => {
    if (!username || workspace !== "history") return;
    api.history().then((result) => setHistoryItems(result.items)).catch(() => setHistoryItems([]));
  }, [workspace, username]);

  async function refresh() {
    setRefreshing(true);
    try { setData(await api.refresh()); } finally { setRefreshing(false); }
  }

  async function logout() {
    await api.logout();
    setUsername(null);
    setData(null);
  }

  if (loading) return <div className="boot-screen"><Activity size={28} /><span>INITIALIZING KINGMODEL</span></div>;
  if (!username) return <LoginPage onLogin={(name) => { setUsername(name); setLoading(true); loadDashboard().finally(() => setLoading(false)); }} />;
  if (!data) return <div className="boot-screen"><ShieldAlert size={28} /><span>暂无可用市场快照</span></div>;

  const freshnessLabel = data.meta.freshness === "live" ? "实时" : data.meta.freshness === "stale" ? "延迟" : "核验快照";
  return <div className="app-shell">
    <aside className={sidebarOpen ? "sidebar open" : "sidebar"}>
      <div className="sidebar-brand"><Activity size={19} /><strong>KINGMODEL</strong><button onClick={() => setSidebarOpen(false)} aria-label="关闭导航"><X size={18} /></button></div>
      <nav>{nav.map((item) => { const Icon = item.icon; return <button key={item.id} className={workspace === item.id ? "active" : ""} onClick={() => { setWorkspace(item.id); setSidebarOpen(false); }}><Icon size={17} /><span>{item.label}</span></button>; })}</nav>
      <div className="sidebar-foot"><div><span className={`status-dot ${data.meta.freshness}`} /><span>数据层</span><strong>{freshnessLabel}</strong></div><button onClick={logout}><LogOut size={16} />退出</button></div>
    </aside>
    <main className="main-shell">
      <header className="topbar">
        <button className="menu-button" onClick={() => setSidebarOpen(true)}><Menu size={19} /></button>
        <div className="market-title"><span>{nav.find((item) => item.id === workspace)?.label}</span><h1>{data.meta.trade_date}<em>{data.meta.version_label ?? "可信快照"}</em><ChevronDown size={15} /></h1></div>
        <div className="topbar-meta"><span><Clock3 size={14} />{new Date(data.meta.updated_at).toLocaleString("zh-CN", { hour12: false })}</span><span className={`source-badge ${data.meta.freshness}`}>{data.meta.source}</span><button className="icon-button"><Bell size={17} /><i>{data.alerts.length}</i></button><button className="refresh-button" onClick={refresh} disabled={refreshing} title="只调用免费接口与本地缓存；关键数据才允许后端受控调用通达信"><RefreshCw size={15} className={refreshing ? "spinning" : ""} />{refreshing ? "刷新中" : "省Token刷新"}</button></div>
      </header>
      {data.meta.warning ? <div className={`data-warning ${data.meta.freshness}`}><ShieldAlert size={15} />{data.meta.warning}</div> : null}
      <div className="content-shell">{workspace === "cockpit" ? <Cockpit data={data} /> : workspace === "settings" ? <SettingsPage username={username} collection={data.collection_status} mlSystem={data.ml_system} /> : <SecondaryWorkspace workspace={workspace} data={data} historyItems={historyItems} />}</div>
    </main>
  </div>;
}
