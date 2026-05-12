import { useState } from 'react';
import { fulltextSearch } from '../api';
import { useNavigate } from 'react-router-dom';

export default function Search() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [history, setHistory] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem('search_history') || '[]'); } catch { return []; }
  });
  const navigate = useNavigate();

  const handleSearch = async (q?: string) => {
    const term = q || query;
    if (!term.trim()) return;
    setQuery(term);
    setLoading(true);
    setSearched(true);
    try {
      const res = await fulltextSearch(term);
      setResults(res.data.items);
      setTotal(res.data.total);
      const newHistory = [term, ...history.filter(h => h !== term)].slice(0, 8);
      setHistory(newHistory);
      localStorage.setItem('search_history', JSON.stringify(newHistory));
    } catch {
      setResults([]); setTotal(0);
    }
    setLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 page-enter">
      {/* Search input */}
      <div className="relative mb-6">
        <span className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400 text-lg">🔍</span>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="搜索书名、作者或全文内容..."
          className="search-pill dark:bg-gray-700 dark:text-gray-200 dark:placeholder-gray-500"
        />
      </div>

      {/* Search history */}
      {!searched && history.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-gray-500">最近搜索</span>
            <button onClick={() => { setHistory([]); localStorage.removeItem('search_history'); }}
              className="text-xs text-gray-400 hover:text-gray-600">清除</button>
          </div>
          <div className="flex flex-wrap gap-2">
            {history.map(h => (
              <button key={h} onClick={() => handleSearch(h)}
                className="px-3 py-1.5 rounded-full text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-500 hover:border-green-300 transition-colors">
                {h}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {searched && (
        <div>
          <p className="text-sm text-gray-500 mb-4">
            {loading ? '搜索中...' : `找到 ${total} 条结果`}
          </p>
          {results.length === 0 && !loading && (
            <div className="text-center py-16">
              <span className="text-5xl mb-4 block">🔍</span>
              <p className="text-gray-400">未找到相关内容</p>
            </div>
          )}
          <div className="space-y-3">
            {results.map((item, i) => (
              <div key={i}
                className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 hover:border-green-200 dark:hover:border-green-600 cursor-pointer transition-colors flex gap-4"
                onClick={() => navigate(`/reader/${item.book_id}`)}>
                <div className="w-10 h-[53px] rounded overflow-hidden flex-shrink-0 bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white text-xs">
                  {item.title?.slice(0, 2) || '📖'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className="font-medium text-sm text-green-600 truncate">{item.title}</h4>
                    <span className="text-xs text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded ml-2 flex-shrink-0">
                      {item.format?.toUpperCase()}
                    </span>
                  </div>
                  {item.author && <p className="text-xs text-gray-400 mb-1">{item.author}</p>}
                  {item.snippet && (
                    <p className="text-sm text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-2">{item.snippet}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
