import { useEffect, useRef, useState } from 'react';
import { createHighlight } from '../api';

interface Props {
  bookId: number;
  onProgress: (p: { currentPage: number; totalPages: number; percent: number; chapter: string }) => void;
  pageMode?: boolean;
  currentPage?: number;
  onPageTotal?: (total: number) => void;
  totalPages?: number;
}

const PRELOAD_RANGE = 2;

export default function PdfReader({ bookId, onProgress, pageMode, currentPage, onPageTotal, totalPages: externalTotalPages }: Props) {
  const [totalPages, setTotalPages] = useState(externalTotalPages || 0);
  const [displayPage, setDisplayPage] = useState(1);
  const [preloaded, setPreloaded] = useState<Set<number>>(new Set());
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(!externalTotalPages);
  const containerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Get page count from backend (skip if totalPages provided by parent)
  useEffect(() => {
    if (externalTotalPages) {
      setTotalPages(externalTotalPages);
      setLoading(false);
      return;
    }
    if (totalPages > 0) return;
    setError('');
    fetch(`/api/reader/${bookId}/content`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(data => {
        const total = data.total_pages || 0;
        setTotalPages(total);
        setDisplayPage(1);
        onPageTotal?.(total);
        onProgress({ currentPage: 1, totalPages: total, percent: total > 0 ? Math.round(100 / total) : 0, chapter: '' });
        setLoading(false);
      })
      .catch(e => { setError(e.message || 'Failed'); setLoading(false); });
  }, [bookId]);

  // Handle external page changes (from Reader keyboard/click)
  useEffect(() => {
    if (pageMode && currentPage && currentPage >= 1 && currentPage <= totalPages) {
      setDisplayPage(currentPage);
    }
  }, [currentPage, pageMode, totalPages]);

  // Preload nearby pages
  useEffect(() => {
    if (totalPages === 0) return;
    const range: number[] = [];
    for (let i = Math.max(1, displayPage - PRELOAD_RANGE); i <= Math.min(totalPages, displayPage + PRELOAD_RANGE); i++) {
      if (!preloaded.has(i)) range.push(i);
    }
    if (range.length === 0) return;
    const updated = new Set(preloaded);
    range.forEach(p => updated.add(p));
    setPreloaded(updated);
  }, [displayPage, totalPages]);

  // IntersectionObserver for scroll mode
  useEffect(() => {
    if (pageMode || totalPages === 0) return;
    observerRef.current = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter(e => e.isIntersecting);
        if (visible.length > 0) {
          const pageEl = visible[0].target as HTMLElement;
          const page = parseInt(pageEl.dataset.page || '1');
          const percent = totalPages > 0 ? Math.round((page / totalPages) * 100) : 0;
          onProgress({ currentPage: page, totalPages, percent, chapter: '' });
        }
      },
      { root: containerRef.current, threshold: 0.5 }
    );
    return () => observerRef.current?.disconnect();
  }, [totalPages, pageMode, onProgress]);

  const handleTextSelect = () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (text && text.length > 5 && containerRef.current?.contains(selection?.anchorNode as Node)) {
      createHighlight({ book_id: bookId, content: text, page: pageMode ? (currentPage || 1) : 1, color: 'yellow' }).catch(() => {});
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full text-(--color-text-secondary)">加载 PDF...</div>;
  }

  if (error || totalPages === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-400 mb-2">PDF 加载失败</p>
          <p className="text-xs text-(--color-text-secondary)">{error || '无法获取页数'}</p>
        </div>
      </div>
    );
  }

  // Page mode: single page
  if (pageMode) {
    // Preload adjacent pages in hidden elements
    const preloadPages = [];
    for (let p = Math.max(1, displayPage - PRELOAD_RANGE); p <= Math.min(totalPages, displayPage + PRELOAD_RANGE); p++) {
      if (p !== displayPage) {
        preloadPages.push(
          <img key={`preload-${p}`} src={`/api/reader/${bookId}/page/${p - 1}`} alt=""
            className="hidden" loading="eager" />
        );
      }
    }
    return (
      <div className="flex flex-col items-center justify-center h-full w-full relative" onMouseUp={handleTextSelect}>
        {preloadPages}
        <div className="flex-1 flex items-center justify-center p-4" style={{ maxWidth: '900px', width: '100%' }}>
          <div key={displayPage} className="page-flip-enter w-full flex flex-col items-center">
            {preloaded.has(displayPage)
              ? <img src={`/api/reader/${bookId}/page/${displayPage - 1}`} alt={`Page ${displayPage}`}
                  className="pdf-page-img" />
              : <div className="skeleton rounded" style={{ width: '800px', height: 'min(100vh - 200px, 1100px)' }} />}
          </div>
        </div>
        <div className="reader-page-nav">
          <button onClick={() => { const p = displayPage - 1; if (p >= 1) { setDisplayPage(p); onProgress({ currentPage: p, totalPages, percent: Math.round((p / totalPages) * 100), chapter: '' }); } }}
            disabled={displayPage <= 1}>‹</button>
          <span className="page-indicator">{displayPage} / {totalPages}</span>
          <button onClick={() => { const p = displayPage + 1; if (p <= totalPages) { setDisplayPage(p); onProgress({ currentPage: p, totalPages, percent: Math.round((p / totalPages) * 100), chapter: '' }); } }}
            disabled={displayPage >= totalPages}>›</button>
        </div>
      </div>
    );
  }

  // Scroll mode
  const pageElements = [];
  const start = Math.max(1, displayPage - 3);
  const end = Math.min(totalPages, displayPage + 5);

  for (let i = start; i <= end; i++) {
    pageElements.push(
      <div key={i} ref={(el) => { if (el) pageRefs.current.set(i, el); }} data-page={i}
        className="flex flex-col items-center" style={{ width: '850px', maxWidth: '100%' }}>
        <img src={`/api/reader/${bookId}/page/${i - 1}`} alt={`Page ${i}`}
          className="w-full h-auto block rounded shadow-lg" loading="lazy"
          style={{ boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }} />
        <div className="text-center text-xs text-(--color-text-secondary) py-3">{i}</div>
      </div>
    );
  }

  return (
    <div className="pdf-container" ref={containerRef} onMouseUp={handleTextSelect}>
      <div className="flex flex-col items-center py-4 gap-2">
        {start > 1 && <div className="text-xs text-(--color-text-secondary) py-8">↑ 向上滚动浏览更多 ↑</div>}
        {pageElements}
        {end < totalPages && <div className="text-xs text-(--color-text-secondary) py-8">↓ 继续滚动浏览更多 ↓</div>}
      </div>
    </div>
  );
}
