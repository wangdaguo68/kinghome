import { useEffect, useState } from 'react';
import { getProviders, createProvider, updateProvider, deleteProvider, testProviderConnection } from '../api';

interface Provider {
  id: number; name: string; base_url: string; api_key: string; model_id: string;
  is_active: boolean; created_at: string;
}

export default function Settings() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  // Form state
  const [name, setName] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelId, setModelId] = useState('');
  const [isActive, setIsActive] = useState(false);

  const fetchProviders = async () => {
    const r = await getProviders();
    setProviders(r.data);
  };

  useEffect(() => { fetchProviders(); }, []);

  const resetForm = () => {
    setName(''); setBaseUrl(''); setApiKey(''); setModelId(''); setIsActive(false);
    setShowForm(false); setEditingId(null); setTestResult(null);
  };

  const handleEdit = (p: Provider) => {
    setName(p.name); setBaseUrl(p.base_url); setApiKey(''); setModelId(p.model_id);
    setIsActive(p.is_active); setEditingId(p.id); setShowForm(true); setTestResult(null);
  };

  const handleSave = async () => {
    if (!name || !baseUrl || !modelId) return;
    try {
      if (editingId) {
        await updateProvider(editingId, { name, base_url: baseUrl, api_key: apiKey || undefined, model_id: modelId, is_active: isActive });
      } else {
        await createProvider({ name, base_url: baseUrl, api_key: apiKey, model_id: modelId, is_active: isActive });
      }
      resetForm();
      fetchProviders();
    } catch (e: any) {
      alert('保存失败: ' + (e.response?.data?.detail || e.message));
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定删除这个配置？')) return;
    await deleteProvider(id);
    fetchProviders();
  };

  const handleTest = async () => {
    if (!baseUrl || !modelId) return;
    setTesting(true);
    setTestResult(null);
    try {
      const r = await testProviderConnection({ base_url: baseUrl, api_key: apiKey, model_id: modelId });
      setTestResult(r.data);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message || '请求失败' });
    }
    setTesting(false);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 page-enter">
      <h2 className="text-xl font-semibold mb-2 text-(--color-text)">设置</h2>
      <p className="text-sm text-(--color-text-secondary) mb-8">配置 AI 大模型连接</p>

      {/* Provider list */}
      {providers.map(p => (
        <div key={p.id} className="settings-section">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3">
                <span className="font-medium text-(--color-text)">{p.name}</span>
                {p.is_active && <span className="w-2 h-2 rounded-full bg-(--color-primary)" title="当前使用" />}
              </div>
              <p className="text-sm text-(--color-text-secondary) mt-1">{p.model_id}</p>
              <p className="text-xs text-(--color-text-secondary)">{p.base_url}</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleEdit(p)}
                className="px-3 py-1.5 text-sm text-(--color-text-secondary) hover:text-(--color-primary) border border-(--color-border) rounded-lg transition-colors">
                编辑
              </button>
              <button onClick={() => handleDelete(p.id)}
                className="px-3 py-1.5 text-sm text-(--color-text-secondary) hover:text-red-400 border border-(--color-border) rounded-lg transition-colors">
                删除
              </button>
            </div>
          </div>
        </div>
      ))}

      {!showForm && (
        <button onClick={() => { resetForm(); setShowForm(true); }}
          className="w-full py-3 border-2 border-dashed border-(--color-border) rounded-xl text-sm text-(--color-text-secondary) hover:text-(--color-primary) hover:border-(--color-primary) transition-colors">
          + 添加模型配置
        </button>
      )}

      {/* Add/Edit form */}
      {showForm && (
        <div className="settings-section mt-4">
          <h3 className="font-medium mb-5 text-(--color-text)">{editingId ? '编辑配置' : '添加模型配置'}</h3>

          <div className="space-y-4">
            <div>
              <label className="settings-label">名称</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)}
                placeholder="例如: DeepSeek, OpenAI, 本地Ollama"
                className="settings-input" />
            </div>
            <div>
              <label className="settings-label">API 地址 (Base URL)</label>
              <input type="text" value={baseUrl} onChange={e => setBaseUrl(e.target.value)}
                placeholder="例如: https://api.deepseek.com/v1"
                className="settings-input" />
            </div>
            <div>
              <label className="settings-label">API Key</label>
              <input type="password" value={apiKey} onChange={e => setApiKey(e.target.value)}
                placeholder={editingId ? '留空则不修改' : 'sk-xxx'}
                className="settings-input" />
            </div>
            <div>
              <label className="settings-label">模型 ID</label>
              <input type="text" value={modelId} onChange={e => setModelId(e.target.value)}
                placeholder="例如: deepseek-chat"
                className="settings-input" />
            </div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={isActive} onChange={e => setIsActive(e.target.checked)} />
              <span className="text-sm text-(--color-text-secondary)">设为默认模型</span>
            </label>
          </div>

          {/* Test result */}
          {testResult && (
            <div className={`test-result ${testResult.success ? 'test-success' : 'test-fail'}`}>
              {testResult.success ? (
                <div>
                  <p className="font-medium">连接成功</p>
                  <p className="text-xs mt-1">延迟: {testResult.latency_ms}ms</p>
                  <p className="text-xs mt-0.5">响应: {testResult.response}</p>
                </div>
              ) : (
                <div>
                  <p className="font-medium">连接失败</p>
                  <p className="text-xs mt-1">{testResult.error}</p>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-5">
            <button onClick={handleSave}
              className="px-5 py-2 bg-(--color-primary) text-(--color-bg) rounded-lg text-sm font-medium hover:bg-(--color-primary-dark) transition-colors">
              保存
            </button>
            <button onClick={handleTest} disabled={testing}
              className="px-5 py-2 border border-(--color-border) rounded-lg text-sm text-(--color-text-secondary) hover:border-(--color-primary) disabled:opacity-50 transition-colors">
              {testing ? '测试中...' : '测试连接'}
            </button>
            <button onClick={resetForm}
              className="px-5 py-2 text-sm text-(--color-text-secondary) hover:text-(--color-text) transition-colors">
              取消
            </button>
          </div>
        </div>
      )}

      {/* Quick preset buttons */}
      {!showForm && (
        <div className="mt-8">
          <p className="text-sm text-(--color-text-secondary) mb-3">快速配置</p>
          <div className="grid grid-cols-2 gap-3">
            {[
              { name: 'DeepSeek', url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
              { name: 'OpenAI', url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
              { name: '本地 Ollama', url: 'http://localhost:11434/v1', model: 'qwen2.5:7b' },
              { name: '通义千问', url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus' },
            ].map(preset => (
              <button key={preset.name} onClick={() => {
                setName(preset.name); setBaseUrl(preset.url); setModelId(preset.model);
                setApiKey(''); setIsActive(false); setShowForm(true);
              }}
                className="p-3 rounded-xl border border-(--color-border) text-left text-sm hover:border-(--color-primary) transition-colors text-(--color-text)">
                <p className="font-medium">{preset.name}</p>
                <p className="text-xs text-(--color-text-secondary) mt-0.5 truncate">{preset.url}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
