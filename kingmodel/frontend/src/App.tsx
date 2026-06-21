import { useCallback, useEffect, useState } from "react";
import { Activity, Bell, BookOpenCheck, Boxes, ChevronDown, Clock3, Database, GitBranch, History, LayoutDashboard, LogOut, Menu, RefreshCw, ScanSearch, Settings, ShieldAlert, Target, X } from "lucide-react";
import { api } from "./api";
import { Cockpit } from "./components/Cockpit";
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

function SecondaryWorkspace({ workspace, data }: { workspace: Workspace; data: DashboardData }) {
  const item = nav.find((entry) => entry.id === workspace)!;
  if (workspace === "map" || workspace === "sectors") {
    return <div className="workspace-page"><div className="page-heading"><span>MARKET STRUCTURE</span><h1>{item.label}</h1><p>从资金迁移、持续性和修复能力解释主线，而不是只看当日涨幅。</p></div><div className="sector-board">{data.mainlines.map((line) => <article key={line.name}><div><small>{line.role}</small><h2>{line.name}</h2><p>{line.flow}</p></div><strong>{line.score}</strong><footer>{line.tags.map((tag) => <span key={tag}>{tag}</span>)}</footer></article>)}</div></div>;
  }
  if (workspace === "cores") {
    return <div className="workspace-page"><div className="page-heading"><span>CORE CANDIDATES</span><h1>{item.label}</h1><p>核心地位来自主动性和板块影响力，不等于静态涨幅排名。</p></div><div className="core-cards">{data.cores.map((core) => <article key={core.code}><span>{core.kind}</span><h2>{core.name}<small>{core.code}</small></h2><strong>{core.score}</strong><p>{core.evidence}</p><button>查看评分依据</button></article>)}</div></div>;
  }
  if (workspace === "sentiment") {
    return <div className="workspace-page"><div className="page-heading"><span>OVERNIGHT EXPECTATION</span><h1>{item.label}</h1><p>把舆情转换成次日待验证条件，不把传播热度当成真实资金。</p></div><div className="sentiment-board">{data.sentiment.map((entry) => <article key={entry.topic}><div className="heat">{entry.heat}</div><div><span>拥挤度 {entry.crowding}</span><h2>{entry.topic}</h2><p>{entry.catalyst}</p><footer>次日验证：{entry.validation}</footer></div></article>)}</div></div>;
  }
  return <div className="workspace-page"><div className="page-heading"><span>WORKSPACE</span><h1>{item.label}</h1><p>该工作区已连接统一快照和认证结构，后续数据将随采集任务持续沉淀。</p></div><div className="empty-workspace"><Database size={34} /><h2>等待实时数据沉淀</h2><p>当前模式：{data.meta.freshness} · 来源：{data.meta.source}</p></div></div>;
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
        <div className="market-title"><span>{nav.find((item) => item.id === workspace)?.label}</span><h1>{data.meta.trade_date}<ChevronDown size={15} /></h1></div>
        <div className="topbar-meta"><span><Clock3 size={14} />{new Date(data.meta.updated_at).toLocaleString("zh-CN", { hour12: false })}</span><span className={`source-badge ${data.meta.freshness}`}>{data.meta.source}</span><button className="icon-button"><Bell size={17} /><i>{data.alerts.length}</i></button><button className="refresh-button" onClick={refresh} disabled={refreshing}><RefreshCw size={15} className={refreshing ? "spinning" : ""} />{refreshing ? "刷新中" : "刷新"}</button></div>
      </header>
      {data.meta.warning ? <div className={`data-warning ${data.meta.freshness}`}><ShieldAlert size={15} />{data.meta.warning}</div> : null}
      <div className="content-shell">{workspace === "cockpit" ? <Cockpit data={data} /> : workspace === "settings" ? <SettingsPage username={username} /> : <SecondaryWorkspace workspace={workspace} data={data} />}</div>
    </main>
  </div>;
}
