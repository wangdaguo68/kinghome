import { FormEvent, useState } from "react";
import { BrainCircuit, CheckCircle2, DatabaseZap, KeyRound, LockKeyhole, ShieldCheck } from "lucide-react";
import { api } from "../api";
import type { DashboardData } from "../types";

const STAGE_LABEL = { rule_only: "规则主导", shadow_learning: "影子学习", assisted: "模型辅助", live_eligible: "具备实盘评审资格" } as const;

export function SettingsPage({ username, collection, mlSystem }: { username: string; collection: DashboardData["collection_status"]; mlSystem?: DashboardData["ml_system"] }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    if (!currentPassword || !newPassword || !confirmation) {
      setMessage({ kind: "error", text: "请完整填写三个密码字段" });
      return;
    }
    if (newPassword !== confirmation) {
      setMessage({ kind: "error", text: "两次输入的新密码不一致" });
      return;
    }

    setSubmitting(true);
    try {
      await api.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmation("");
      setMessage({ kind: "success", text: "密码已修改，当前登录状态保持不变" });
    } catch (error) {
      setMessage({ kind: "error", text: error instanceof Error ? error.message : "密码修改失败" });
    } finally {
      setSubmitting(false);
    }
  }

  return <div className="workspace-page settings-page">
    <div className="page-heading">
      <span>SYSTEM / ACCOUNT SECURITY</span>
      <h1>系统设置</h1>
      <p>管理账户密码、免费收盘任务和通达信每日硬预算。</p>
    </div>
    <section className="budget-card">
      <header><div className="security-icon"><DatabaseZap size={20} /></div><div><span>DATA BUDGET</span><h2>通达信 Token 防护</h2></div><strong>{collection.tdx_calls_used}<small> / {collection.tdx_daily_limit}</small></strong></header>
      <div className="budget-body">
        <div><ShieldCheck size={18} /><span><b>手动刷新零消耗</b>页面刷新只调用免费接口与本地缓存，不触发通达信逐股分析。</span></div>
        <dl><div><dt>预算交易日</dt><dd>{collection.trade_date}</dd></div><div><dt>收盘任务</dt><dd>{collection.job?.status ?? "未执行"}</dd></div><div><dt>免费采集尝试</dt><dd>{collection.job?.free_attempts ?? 0}</dd></div></dl>
        {collection.tdx_calls.length ? <ul>{collection.tdx_calls.map((item) => <li key={`${item.code}-${item.called_at}`}><code>{item.code}</code><span>{item.called_at}</span><b>{item.status}</b></li>)}</ul> : <p>今日尚未调用通达信逐股补查。</p>}
      </div>
    </section>
    <section className="model-card">
      <header><div className="model-icon"><BrainCircuit size={21} /></div><div><span>MODEL LIFECYCLE</span><h2>机器学习引擎</h2></div><strong>{mlSystem ? STAGE_LABEL[mlSystem.stage] : "等待状态"}</strong></header>
      <div className="model-body">
        <div className="model-gates">
          {[{ day: 20, label: "开始训练" }, { day: 60, label: "辅助评分" }, { day: 120, label: "实盘评审" }].map((gate) => {
            const current = mlSystem?.outcome_days ?? 0;
            return <article key={gate.day} className={current >= gate.day ? "reached" : ""}><span>{gate.day}<i>日</i></span><strong>{gate.label}</strong><div><i style={{ width: `${Math.min(100, current / gate.day * 100)}%` }} /></div><small>{Math.min(current, gate.day)} / {gate.day}</small></article>;
          })}
        </div>
        <dl><div><dt>特征交易日</dt><dd>{mlSystem?.feature_days ?? 0}</dd></div><div><dt>结果交易日</dt><dd>{mlSystem?.outcome_days ?? 0}</dd></div><div><dt>Champion</dt><dd>{mlSystem?.champion_count ?? 0}</dd></div><div><dt>Challenger</dt><dd>{mlSystem?.challenger_count ?? 0}</dd></div></dl>
        <p><ShieldCheck size={15} />未满120个结果交易日，或正期望、盈亏比、回撤、校准任一不达标，模型都不会改变正式计划。</p>
      </div>
    </section>
    <section className="security-card">
      <header>
        <div className="security-icon"><LockKeyhole size={20} /></div>
        <div><span>账户安全</span><h2>修改登录密码</h2></div>
        <code>{username}</code>
      </header>
      <form onSubmit={submit}>
        <label>当前密码<input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" /></label>
        <div className="new-password-row">
          <label>新密码<input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" /></label>
          <label>确认新密码<input type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" /></label>
        </div>
        {message ? <div className={`password-message ${message.kind}`}>{message.kind === "success" ? <CheckCircle2 size={15} /> : <KeyRound size={15} />}{message.text}</div> : null}
        <footer><p>修改后旧密码立即失效，当前会话继续有效。</p><button type="submit" disabled={submitting}>{submitting ? "正在保存…" : "保存新密码"}</button></footer>
      </form>
    </section>
  </div>;
}
