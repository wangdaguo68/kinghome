import { useCallback, useEffect, useState } from "react";
import { Activity, Bell, BookOpenCheck, Boxes, ChevronDown, Clock3, Database, GitBranch, History, LayoutDashboard, LogOut, Menu, RefreshCw, ScanSearch, Settings, ShieldAlert, Target, X } from "lucide-react";
import { api } from "./api";
import { Cockpit } from "./components/Cockpit";
import { FlowMap } from "./components/FlowMap";
import { LoginPage } from "./components/LoginPage";
import { SettingsPage } from "./components/SettingsPage";
import type { DashboardData, Workspace } from "./types";

const nav: Array<{ id: Workspace; label: string; icon: typeof Activity }> = [
  { id: "cockpit", label: "决策驾驶舱", icon: LayoutDashboard },
  { id: "map", label: "市场图谱", icon: GitBranch },
  { id: "sectors", label: "主线板块", icon: Boxes },
  { id: "cores", label: "核心标的", icon: Target },
  { id: "sentiment", label: "隔夜舆情", icon: ScanSearch },
  { id: "review", label: "盘后复盘", icon: BookOpenCheck },
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
    <div className="capacity-core-list workspace-capacity">{(data.capacity_cores ?? []).slice(0, 12).map((item) => <article key={item.code} className={!item.tradable ? "disabled" : ""}>
      <div className="capacity-rank">#{item.rank}</div>
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
    <div className="sentiment-board">{data.sentiment.map((entry) => <article key={entry.topic}><div className="heat">{entry.heat}</div><div><span>拥挤度 {entry.crowding}</span><h2>{entry.topic}</h2><p>{entry.catalyst}</p><footer>次日验证：{entry.validation}</footer></div></article>)}</div>
  </div>;
}

function ReviewWorkspace({ data }: { data: DashboardData }) {
  const review = data.ml_review;
  return <div className="workspace-page"><div className="page-heading"><span>MODEL OUTCOMES</span><h1>盘后复盘</h1><p>按未来收益标签回看计划质量，同时把当日主线/联动作为盘后复盘信号写回次日计划。</p></div>
    <div className="review-summary">{(review?.summary ?? []).map((entry) => <article key={entry.horizon}><span>{entry.horizon}D</span><div><small>样本</small><strong>{entry.samples}</strong></div><div><small>胜率</small><strong>{entry.win_rate === null ? "—" : `${(entry.win_rate * 100).toFixed(1)}%`}</strong></div><div><small>平均净收益</small><strong className={(entry.average_return ?? 0) >= 0 ? "up" : "down"}>{entry.average_return === null ? "—" : `${entry.average_return >= 0 ? "+" : ""}${(entry.average_return * 100).toFixed(2)}%`}</strong></div></article>)}</div>
    {review?.items.length ? <div className="review-table"><header><span>日期 / 标的</span><span>周期</span><span>净收益</span><span>MFE</span><span>MAE</span><span>可成交</span></header>{review.items.slice(0, 40).map((entry) => <div key={`${entry.trade_date}-${entry.code}-${entry.horizon}`}><span><b>{entry.name}</b><small>{entry.trade_date} · {entry.code}</small></span><span>{entry.horizon}日</span><span className={entry.net_return >= 0 ? "up" : "down"}>{entry.tradable ? `${entry.net_return >= 0 ? "+" : ""}${(entry.net_return * 100).toFixed(2)}%` : "—"}</span><span className="up">+{(entry.mfe * 100).toFixed(2)}%</span><span className="down">{(entry.mae * 100).toFixed(2)}%</span><span>{entry.tradable ? "是" : entry.blocked_reason ?? "否"}</span></div>)}</div> : <div className="empty-workspace"><Database size={34} /><h2>等待未来收益标签</h2><p>影子计划会在后续交易日自动回填，不调用通达信。</p></div>}
  </div>;
}

function SecondaryWorkspace({ workspace, data }: { workspace: Workspace; data: DashboardData }) {
  const item = nav.find((entry) => entry.id === workspace)!;
  if (workspace === "map") return <MarketMapWorkspace data={data} />;
  if (workspace === "sectors") return <SectorsWorkspace data={data} />;
  if (workspace === "cores") return <CoresWorkspace data={data} />;
  if (workspace === "sentiment") return <SentimentWorkspace data={data} />;
  if (workspace === "review") return <ReviewWorkspace data={data} />;
  return <div className="workspace-page"><div className="page-heading"><span>WORKSPACE</span><h1>{item.label}</h1><p>该工作区已连接统一快照和认证结构，后续数据会随采集任务持续沉淀。</p></div><div className="empty-workspace"><Database size={34} /><h2>等待数据沉淀</h2><p>当前模式：{data.meta.freshness} · 来源：{data.meta.source}</p></div></div>;
}

export default function App() {
  const [username, setUsername] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
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
      <div className="content-shell">{workspace === "cockpit" ? <Cockpit data={data} /> : workspace === "settings" ? <SettingsPage username={username} collection={data.collection_status} mlSystem={data.ml_system} /> : <SecondaryWorkspace workspace={workspace} data={data} />}</div>
    </main>
  </div>;
}
