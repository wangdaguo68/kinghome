import { useState, type FormEvent } from "react";
import { Activity, ArrowRight, LockKeyhole } from "lucide-react";
import { api } from "../api";

export function LoginPage({ onLogin }: { onLogin: (username: string) => void }) {
  const [username, setUsername] = useState("king");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const user = await api.login(username, password);
      onLogin(user.username);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return <main className="login-shell">
    <div className="login-grid" aria-hidden="true" />
    <section className="login-manifesto">
      <div className="brand-mark"><Activity size={22} /><span>KINGMODEL</span></div>
      <div className="manifesto-index">01 / 决策系统</div>
      <h1>把市场噪声<br /><em>压缩成行动边界。</em></h1>
      <p>先判断哪里能赚钱，再判断用什么方式赚钱。只交易主线中具有真实影响力的核心。</p>
      <div className="manifesto-status"><span className="pulse" /> MARKET INTELLIGENCE TERMINAL</div>
    </section>
    <section className="login-panel">
      <div className="login-card">
        <LockKeyhole size={24} />
        <div><span className="eyebrow">PRIVATE ACCESS</span><h2>进入决策台</h2></div>
        <form onSubmit={submit}>
          <label>账户<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" /></label>
          <label>密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" autoFocus /></label>
          {error ? <p className="form-error">{error}</p> : null}
          <button disabled={loading || !password}>{loading ? "验证中…" : "登录"}<ArrowRight size={17} /></button>
        </form>
        <p className="security-note">测试阶段使用 HTTP，请勿复用其他重要密码。</p>
      </div>
    </section>
  </main>;
}
