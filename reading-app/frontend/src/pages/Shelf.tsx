import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getBooks, getContinueReading, getScanStatus, startScan, addToShelf, getCategories } from '../api';

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
  const [sort, setSort] = useState('last_read_at');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanInfo, setScanInfo] = useState<any>(null);
  const [continueBooks, setContinueBooks] = useState<Book[]>([]);
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
    getContinueReading(20).then(r => setContinueBooks(r.data.items || [])).catch(() => {});
  }, []);

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

  const getCoverFallback = (book: Book) => {
    const idx = book.id % COVER_GRADIENTS.length;
    const [c1, c2] = COVER_GRADIENTS[idx];
    return { background: `linear-gradient(135deg, ${c1}, ${c2})` };
  };

  const getThumbUrl = (coverPath: string) => coverPath.replace(/\.jpg$/i, '_thumb.jpg');

  const handleImgError = useCallback((e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    const bookId = parseInt(img.dataset.bookId || '0');
    const idx = bookId % COVER_GRADIENTS.length;
    const [c1, c2] = COVER_GRADIENTS[idx];
    img.style.display = 'none';
    const parent = img.parentElement;
    if (parent) {
      parent.style.background = `linear-gradient(135deg, ${c1}, ${c2})`;
    }
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 page-enter">
      {/* Continue Reading Section */}
      {!filter && continueBooks.length > 0 && (
        <div className="mb-8">
          <h3 className="text-sm font-medium text-(--color-text-secondary) mb-3">继续阅读</h3>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {continueBooks.slice(0, 20).map(book => (
              <div key={book.id} className="flex-shrink-0 w-[120px] cursor-pointer group" onClick={() => handleBookClick(book)}>
                <div className="book-cover group-hover:shadow-lg" style={!book.cover_path ? getCoverFallback(book) : undefined}>
                  {book.cover_path
                    ? <img src={getThumbUrl(book.cover_path)} alt={book.title} loading="lazy" data-book-id={book.id}
                        className="w-full h-full object-cover rounded-[4px]" onError={handleImgError} />
                    : <span className="text-xs">{book.title.slice(0, 6)}</span>}
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
              className={`px-4 py-1.5 rounded-full text-sm transition-colors ${(filter || '') === f ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-card-raised) text-(--color-text-secondary) border border-(--color-border) hover:border-(--color-primary)'}`}>
              {{ '': '全部', reading: '在读', want_to_read: '想读', done: '读完' }[f]}
            </button>
          ))}
        </div>
        <select value={selectedCategory} onChange={e => { setSelectedCategory(e.target.value); setPage(1); }}
            className="text-sm border border-(--color-border) bg-(--color-card) rounded-lg px-3 py-1.5 text-(--color-text) outline-none">
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
            className="text-sm border border-(--color-border) bg-(--color-card) rounded-lg px-3 py-1.5 text-(--color-text) outline-none">
            <option value="last_read_at">最近阅读</option>
            <option value="updated_at">最近更新</option>
            <option value="title">书名排序</option>
            <option value="author">作者排序</option>
            <option value="created_at">最近添加</option>
          </select>
          {scanning && scanInfo && (
            <span className="text-xs text-(--color-text-secondary)">扫描中 {scanInfo.processed}/{scanInfo.total}</span>
          )}
          <button onClick={handleScan}
            className="px-4 py-1.5 bg-(--color-primary) text-(--color-bg) rounded-full text-sm hover:bg-(--color-primary-dark) transition-colors font-medium">
            {scanning ? '扫描中...' : '扫描书库'}
          </button>
      </div>

      <div className="text-sm text-(--color-text-secondary) mb-4">共 {total} 本书</div>

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
        <div className="flex flex-col items-center justify-center py-24 text-(--color-text-secondary)">
          <span className="text-5xl mb-4">📚</span>
          <p className="text-lg mb-1">{scanning ? '正在扫描书库...' : '书库还是空的'}</p>
          <p className="text-sm mb-6">{scanning ? '请稍候' : '点击"扫描书库"导入你的书籍'}</p>
          {!scanning && (
            <button onClick={handleScan} className="px-6 py-2 bg-(--color-primary) text-(--color-bg) rounded-full text-sm hover:bg-(--color-primary-dark) font-medium">
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
              <div className="book-cover" style={!book.cover_path ? getCoverFallback(book) : undefined}>
                {book.cover_path
                  ? <img src={getThumbUrl(book.cover_path)} alt={book.title} loading="lazy" data-book-id={book.id}
                      className="w-full h-full object-cover rounded-[4px]" onError={handleImgError} />
                  : <span>{book.title.slice(0, 8)}</span>}
                <span className="book-format-badge">{FORMAT_LABELS[book.format] || book.format}</span>
              </div>
              <div className="book-title">{book.title}</div>
              <div className="book-author">{book.author || '未知作者'}</div>
              {book.subcategory && (
                <div className="text-xs text-(--color-text-secondary) mt-0.5 truncate">{book.category} · {book.subcategory}</div>
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
            className="px-4 py-2 rounded-lg text-sm bg-(--color-card-raised) border border-(--color-border) disabled:opacity-40 hover:border-(--color-primary) transition-colors text-(--color-text)">上一页</button>
          <span className="text-sm leading-10 text-(--color-text-secondary)">{page} / {Math.ceil(total / 48)}</span>
          <button disabled={page >= Math.ceil(total / 48)} onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 rounded-lg text-sm bg-(--color-card-raised) border border-(--color-border) disabled:opacity-40 hover:border-(--color-primary) transition-colors text-(--color-text)">下一页</button>
        </div>
      )}
    </div>
  );
}
