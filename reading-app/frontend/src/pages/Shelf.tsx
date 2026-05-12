import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getBooks, getScanStatus, startScan, addToShelf, getCategories } from '../api';

interface Book {
  id: number; title: string; author: string; format: string;
  cover_path: string; category: string; subcategory: string; progress: any; shelf_status: string | null;
}

const COVER_GRADIENTS = [
  ['#667eea', '#764ba2'], ['#f093fb', '#f5576c'], ['#4facfe', '#00f2fe'],
  ['#43e97b', '#38f9d7'], ['#fa709a', '#fee140'], ['#a18cd1', '#fbc2eb'],
  ['#fccb90', '#d57eeb'], ['#e0c3fc', '#8ec5fc'],
];

const FORMAT_LABELS: Record<string, string> = { pdf: 'PDF', epub: 'EPUB', mobi: 'MOBI' };

export default function Shelf() {
  const [books, setBooks] = useState<Book[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState('');
  const [sort, setSort] = useState('updated_at');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanInfo, setScanInfo] = useState<any>(null);
  const navigate = useNavigate();

  const fetchBooks = async () => {
    setLoading(true);
    try {
      const res = await getBooks({ page, page_size: 48, status: filter || undefined, sort, category: selectedCategory || undefined });
      setBooks(res.data.items);
      setTotal(res.data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchBooks(); }, [page, filter, sort, selectedCategory]);

  useEffect(() => {
    getCategories().then(r => setCategories(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    getScanStatus().then(r => {
      setScanInfo(r.data);
      if (!r.data.is_complete) setScanning(true);
    });
  }, []);

  useEffect(() => {
    if (!scanning) return;
    const timer = setInterval(async () => {
      const r = await getScanStatus();
      setScanInfo(r.data);
      if (r.data.is_complete) { setScanning(false); fetchBooks(); }
    }, 2000);
    return () => clearInterval(timer);
  }, [scanning]);

  const handleScan = async () => {
    try { await startScan(); setScanning(true); } catch {}
  };

  const handleBookClick = (book: Book) => {
    addToShelf(book.id, { status: 'reading' }).catch(() => {});
    navigate(`/reader/${book.id}`);
  };

  const getCoverStyle = (book: Book) => {
    if (book.cover_path) return { backgroundImage: `url(${book.cover_path})`, backgroundSize: 'cover' as const, backgroundPosition: 'center' as const };
    const idx = book.id % COVER_GRADIENTS.length;
    const [c1, c2] = COVER_GRADIENTS[idx];
    return { background: `linear-gradient(135deg, ${c1}, ${c2})` };
  };

  const readingBooks = books.filter(b => b.shelf_status === 'reading');

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 page-enter">
      {/* Continue Reading Section */}
      {!filter && readingBooks.length > 0 && (
        <div className="mb-8">
          <h3 className="text-sm font-medium text-gray-500 mb-3">继续阅读</h3>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {readingBooks.slice(0, 6).map(book => (
              <div key={book.id} className="flex-shrink-0 w-[120px] cursor-pointer group" onClick={() => handleBookClick(book)}>
                <div className="book-cover group-hover:shadow-lg" style={getCoverStyle(book)}>
                  {!book.cover_path && <span className="text-xs">{book.title.slice(0, 6)}</span>}
                </div>
                <div className="book-title text-xs">{book.title}</div>
                {book.progress && (
                  <div className="book-progress-bar">
                    <div className="book-progress-fill" style={{ width: `${book.progress.progress_percent}%` }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div className="flex gap-2">
          {(['', 'reading', 'want_to_read', 'done'] as const).map(f => (
            <button key={f} onClick={() => { setFilter(f); setPage(1); }}
              className={`px-4 py-1.5 rounded-full text-sm transition-colors ${(filter || '') === f ? 'bg-green-500 text-white' : 'bg-white dark:bg-gray-800 text-gray-500 border border-gray-200 dark:border-gray-700 hover:border-green-300'}`}>
              {{ '': '全部', reading: '在读', want_to_read: '想读', done: '读完' }[f]}
            </button>
          ))}
        </div>
        <select value={selectedCategory} onChange={e => { setSelectedCategory(e.target.value); setPage(1); }}
            className="text-sm border border-gray-200 dark:border-gray-700 dark:bg-gray-800 rounded-lg px-3 py-1.5 text-gray-500 outline-none">
            <option value="">全部分类</option>
            {categories.map(cat => (
              <optgroup key={cat.category} label={`${cat.category} (${cat.total})`}>
                {cat.subcategories.map((s: any) => (
                  <option key={s.subcategory} value={s.subcategory}>{s.subcategory} ({s.count})</option>
                ))}
              </optgroup>
            ))}
          </select>
          <select value={sort} onChange={e => setSort(e.target.value)}
            className="text-sm border border-gray-200 dark:border-gray-700 dark:bg-gray-800 rounded-lg px-3 py-1.5 text-gray-500 outline-none">
            <option value="updated_at">最近更新</option>
            <option value="title">书名排序</option>
            <option value="author">作者排序</option>
            <option value="created_at">最近添加</option>
          </select>
          {scanning && scanInfo && (
            <span className="text-xs text-gray-400">扫描中 {scanInfo.processed}/{scanInfo.total}</span>
          )}
          <button onClick={handleScan}
            className="px-4 py-1.5 bg-green-500 text-white rounded-full text-sm hover:bg-green-600 transition-colors">
            {scanning ? '扫描中...' : '扫描书库'}
          </button>
      </div>

      <div className="text-sm text-gray-400 mb-4">共 {total} 本书</div>

      {/* Loading skeleton */}
      {loading && (
        <div className="book-grid">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i}>
              <div className="skeleton w-full aspect-[3/4] rounded-md" />
              <div className="skeleton h-4 w-3/4 mt-2" />
              <div className="skeleton h-3 w-1/2 mt-1.5" />
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && books.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-gray-400">
          <span className="text-5xl mb-4">📚</span>
          <p className="text-lg mb-1">{scanning ? '正在扫描书库...' : '书库还是空的'}</p>
          <p className="text-sm mb-6">{scanning ? '请稍候' : '点击"扫描书库"导入你的书籍'}</p>
          {!scanning && (
            <button onClick={handleScan} className="px-6 py-2 bg-green-500 text-white rounded-full text-sm hover:bg-green-600">
              开始扫描
            </button>
          )}
        </div>
      )}

      {/* Book grid */}
      {!loading && (
        <div className="book-grid">
          {books.map(book => (
            <div key={book.id} className="book-card" onClick={() => handleBookClick(book)}>
              <div className="book-cover" style={getCoverStyle(book)}>
                <span className="book-format-badge">{FORMAT_LABELS[book.format] || book.format}</span>
                {!book.cover_path && <span>{book.title.slice(0, 8)}</span>}
              </div>
              <div className="book-title">{book.title}</div>
              <div className="book-author">{book.author || '未知作者'}</div>
              {book.subcategory && (
                <div className="text-xs text-gray-400 mt-0.5 truncate">{book.category} · {book.subcategory}</div>
              )}
              {book.progress && book.progress.progress_percent > 0 && (
                <div className="book-progress-bar">
                  <div className="book-progress-fill" style={{ width: `${book.progress.progress_percent}%` }} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 48 && (
        <div className="flex justify-center gap-4 mt-8">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 rounded-lg text-sm bg-white dark:bg-gray-800 border dark:border-gray-700 disabled:opacity-40 hover:border-green-300 transition-colors">上一页</button>
          <span className="text-sm leading-10 text-gray-400">{page} / {Math.ceil(total / 48)}</span>
          <button disabled={page >= Math.ceil(total / 48)} onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 rounded-lg text-sm bg-white dark:bg-gray-800 border dark:border-gray-700 disabled:opacity-40 hover:border-green-300 transition-colors">下一页</button>
        </div>
      )}
    </div>
  );
}
