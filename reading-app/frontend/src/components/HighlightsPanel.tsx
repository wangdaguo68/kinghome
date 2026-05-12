import { useEffect, useState } from 'react';
import { getHighlights, updateHighlight, deleteHighlight } from '../api';

interface Props {
  bookId: number;
  onClose: () => void;
}

export default function HighlightsPanel({ bookId, onClose }: Props) {
  const [highlights, setHighlights] = useState<any[]>([]);
  const [editingNote, setEditingNote] = useState<number | null>(null);
  const [noteText, setNoteText] = useState('');

  const fetch = async () => {
    const res = await getHighlights(bookId);
    setHighlights(res.data);
  };

  useEffect(() => { fetch(); }, [bookId]);

  const saveNote = async (id: number) => {
    await updateHighlight(id, { note: noteText });
    setEditingNote(null);
    fetch();
  };

  const handleDelete = async (id: number) => {
    await deleteHighlight(id);
    fetch();
  };

  const colors: Record<string, string> = {
    yellow: '#ffc107', green: '#07c160', blue: '#2196f3', red: '#f44336',
  };

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">划线 & 笔记</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
      </div>
      {highlights.length === 0 && <p className="text-sm text-gray-400">还没有任何划线</p>}
      {highlights.map(h => (
        <div key={h.id} className="mb-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div className="flex items-start gap-2 mb-2">
            <span className="w-1 h-full rounded" style={{ background: colors[h.color] || '#ffc107', minWidth: '3px', display: 'inline-block', alignSelf: 'stretch' }} />
            <p className="text-sm flex-1 leading-relaxed">{h.content}</p>
          </div>
          {h.page > 0 && <span className="text-xs text-gray-400 mr-2">第{h.page}页</span>}
          {editingNote === h.id ? (
            <div className="mt-2">
              <textarea value={noteText} onChange={e => setNoteText(e.target.value)}
                className="w-full p-2 text-sm border rounded" rows={3} placeholder="写想法..." />
              <div className="flex gap-2 mt-1">
                <button onClick={() => saveNote(h.id)} className="text-xs text-green-500">保存</button>
                <button onClick={() => setEditingNote(null)} className="text-xs text-gray-400">取消</button>
              </div>
            </div>
          ) : h.note ? (
            <p className="text-sm text-gray-500 mt-1 bg-yellow-50 dark:bg-gray-600 p-2 rounded">{h.note}</p>
          ) : null}
          {!h.note && editingNote !== h.id && (
            <button onClick={() => { setEditingNote(h.id); setNoteText(''); }}
              className="text-xs text-gray-400 mt-1 hover:text-green-500">
              + 写想法
            </button>
          )}
          <button onClick={() => handleDelete(h.id)} className="text-xs text-red-300 mt-1 ml-3 hover:text-red-500">
            删除
          </button>
        </div>
      ))}
    </div>
  );
}
