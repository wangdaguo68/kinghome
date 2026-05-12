import { useEffect, useState, useRef } from 'react';
import { getConversations, createConversation, deleteConversation, getMessages, getActiveProvider } from '../api';
import ReactMarkdown from 'react-markdown';

interface Conv {
  id: number; title: string; model: string; updated_at: string;
}
interface Msg {
  id: number; conversation_id: number; role: string; content: string;
  citations?: { title: string; book_id: number; snippet: string }[] | null;
}

export default function Chat() {
  const [conversations, setConversations] = useState<Conv[]>([]);
  const [activeConv, setActiveConv] = useState<number | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [useRag, setUseRag] = useState(true);
  const [model, setModel] = useState('');
  const [providers, setProviders] = useState<any[]>([]);
  const [editingTitle, setEditingTitle] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getConversations().then(r => setConversations(r.data));
    getActiveProvider().then(r => {
      if (r.data) {
        setModel(r.data.model_id);
        setProviders([r.data]);
      }
    });
  }, []);

  useEffect(() => {
    if (!activeConv) return;
    getMessages(activeConv).then(r => setMessages(r.data));
  }, [activeConv]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  const handleNewChat = async () => {
    const r = await createConversation('新对话', model || undefined);
    setConversations(prev => [r.data, ...prev]);
    setActiveConv(r.data.id);
    setMessages([]);
  };

  const handleDeleteConv = async (id: number) => {
    await deleteConversation(id);
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeConv === id) {
      const remaining = conversations.filter(c => c.id !== id);
      setActiveConv(remaining[0]?.id || null);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    setLoading(true);
    const tempId = Date.now();
    setMessages(prev => [...prev, {
      id: tempId, conversation_id: activeConv || 0, role: 'user', content: input,
    }]);
    const userInput = input;
    setInput('');
    setStreamingText('');

    try {
      const resp = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: activeConv,
          message: userInput,
          model: model || undefined,
          use_rag: useRag,
        }),
      });
      const reader = resp.body?.getReader();
      if (!reader) throw new Error('No response');

      const decoder = new TextDecoder();
      let fullText = '', convId = activeConv, citations: any[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of decoder.decode(value, { stream: true }).split('\n')) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.chunk) { fullText += data.chunk; setStreamingText(fullText); }
              if (data.conv_id) convId = data.conv_id;
              if (data.done) { citations = data.citations || []; setStreamingText(''); }
            } catch {}
          }
        }
      }

      setMessages(prev => [...prev, {
        id: tempId + 1, conversation_id: convId || 0,
        role: 'assistant', content: fullText, citations,
      }]);
      if (convId && !activeConv) setActiveConv(convId);
      getConversations().then(r => setConversations(r.data));
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: tempId + 1, conversation_id: activeConv || 0,
        role: 'assistant', content: `错误: ${err.message || '请求失败'}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="chat-container dark:bg-gray-900">
      <div className="chat-sidebar dark:bg-gray-800 dark:border-gray-700">
        <div className="p-3">
          <button onClick={handleNewChat}
            className="w-full py-2.5 bg-green-500 text-white rounded-lg text-sm font-medium hover:bg-green-600 transition-colors">
            + 新对话
          </button>
        </div>
        <div className="px-2">
          {conversations.map(c => (
            <div key={c.id}
              onClick={() => setActiveConv(c.id)}
              className={`px-3 py-3 rounded-lg cursor-pointer text-sm mb-0.5 flex items-center justify-between group transition-colors ${activeConv === c.id ? 'bg-green-50 dark:bg-green-900/20 text-green-600' : 'hover:bg-gray-50 dark:hover:bg-gray-750'}`}>
              <span className="truncate flex-1" onDoubleClick={() => setEditingTitle(c.id)}>
                {editingTitle === c.id ? (
                  <input autoFocus defaultValue={c.title}
                    onBlur={() => setEditingTitle(null)}
                    onKeyDown={e => { if (e.key === 'Enter') setEditingTitle(null); }}
                    className="w-full border rounded px-1 py-0.5 text-xs outline-none"
                    onClick={e => e.stopPropagation()} />
                ) : c.title}
              </span>
              <button onClick={(e) => { e.stopPropagation(); handleDeleteConv(c.id); }}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 ml-1 text-xs transition-opacity">✕</button>
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-8">暂无对话</p>
          )}
        </div>
      </div>

      <div className="chat-main">
        <div className="flex items-center gap-4 px-5 py-2 border-b border-gray-100 dark:border-gray-700 text-xs">
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input type="checkbox" checked={useRag} onChange={e => setUseRag(e.target.checked)} />
            <span className="text-gray-500">知识库增强</span>
          </label>
          <select value={model} onChange={e => setModel(e.target.value)}
            className="border rounded-lg px-2 py-1 text-xs dark:bg-gray-700 dark:border-gray-600 outline-none">
            {providers.length > 0 ? providers.map(p => (
              <option key={p.id} value={p.model_id}>{p.name} - {p.model_id}</option>
            )) : (
              <>
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="qwen2.5:7b">Qwen 2.5 7B</option>
              </>
            )}
          </select>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && !streamingText && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <p className="text-xl mb-2">AI 知识库助手</p>
              <p className="text-sm mb-8">基于你上万本书籍的知识库，随时提问</p>
              <div className="grid grid-cols-2 gap-3 w-full max-w-lg text-xs">
                {['《思考，快与慢》的核心观点是什么？', '推荐几本关于投资理财的书', '如何提升专注力和效率？', '中国近代史的关键转折点有哪些？'].map(q => (
                  <button key={q} onClick={() => setInput(q)}
                    className="p-3 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-500 text-left transition-colors">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map(m => (
            <div key={m.id} className={`message-bubble ${m.role === 'user' ? 'message-user' : 'message-assistant dark:bg-gray-700 dark:border-gray-600'}`}>
              {m.role === 'assistant' ? (
                <div className="prose prose-sm dark:text-gray-200 max-w-none">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{m.content}</p>
              )}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-600">
                  <p className="text-xs text-gray-400 mb-1">参考书籍</p>
                  {m.citations.map((c, i) => (
                    <span key={i} className="citation dark:bg-gray-600 dark:text-gray-300">{c.title}{c.snippet ? ` · ${c.snippet.slice(0, 50)}...` : ''}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && !streamingText && (
            <div className="message-bubble message-assistant dark:bg-gray-700">
              <p className="text-sm text-gray-400 mb-2">AI 正在思考...</p>
              <div className="typing-dots">
                <span /><span /><span />
              </div>
            </div>
          )}
          {streamingText && (
            <div className="message-bubble message-assistant dark:bg-gray-700">
              <div className="prose prose-sm dark:text-gray-200 max-w-none">
                <ReactMarkdown>{streamingText}</ReactMarkdown>
              </div>
              <div className="typing-dots mt-2">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area dark:bg-gray-800 dark:border-gray-700">
          <div className="flex gap-3">
            <textarea
              value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入问题，基于书库知识回答..."
              rows={2}
              className="flex-1 resize-none border border-gray-200 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-green-400 transition-colors"
            />
            <button onClick={handleSend} disabled={loading || !input.trim()}
              className="px-6 py-3 bg-green-500 text-white rounded-xl text-sm font-medium hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed self-end transition-colors">
              {loading ? '思考中' : '发送'}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2 text-center">Enter 发送 · Shift+Enter 换行</p>
        </div>
      </div>
    </div>
  );
}
