import { FormEvent, useState } from "react";
import { CheckCircle2, KeyRound, LockKeyhole } from "lucide-react";
import { api } from "../api";

export function SettingsPage({ username }: { username: string }) {
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
      <p>管理当前单用户账户的登录密码。</p>
    </div>
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
