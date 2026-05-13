import { useEffect, useRef, useState } from 'react';
import { createHighlight } from '../api';

interface Props {
  bookId: number;
  book: any;
  onProgress: (p: { currentPage: number; totalPages: number; percent: number; chapter: string }) => void;
  pageMode?: boolean;
  currentPage?: number;
  onPageTotal?: (total: number) => void;
}

export default function PdfReader({ bookId, book, onProgress, pageMode, currentPage, onPageTotal }: Props) {
  const [totalPages, setTotalPages] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const [preloaded, setPreloaded] = useState<Set<number>>(new Set());

  useEffect(() => {
    import('pdfjs-dist').then(async (pdfjs: any) => {
      pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/5.7.284/pdf.worker.min.mjs';
      const doc = await pdfjs.getDocument(`/api/reader/${bookId}/file`).promise;
      setTotalPages(doc.numPages);
      onPageTotal?.(doc.numPages);
      onProgress({ currentPage: 1, totalPages: doc.numPages, percent: 0, chapter: '' });
    });
  }, [bookId]);

  // Preload pages around current page
  useEffect(() => {
    if (!pageMode || totalPages === 0) return;
    const page = currentPage || 1;
    const toPreload = new Set<number>();
    for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
      if (!preloaded.has(i)) toPreload.add(i);
    }
    if (toPreload.size === 0) return;
    const updated = new Set(preloaded);
    toPreload.forEach(p => updated.add(p));
    setPreloaded(updated);
  }, [currentPage, totalPages, pageMode, preloaded.size]);

  // Intersection observer for scroll mode
  useEffect(() => {
    if (pageMode) return;
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
  }, [totalPages, pageMode]);

  const handleTextSelect = () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (text && text.length > 5 && containerRef.current?.contains(selection?.anchorNode as Node)) {
      createHighlight({
        book_id: bookId,
        content: text,
        page: pageMode ? (currentPage || 1) : 1,
        color: 'yellow',
      }).catch(() => {});
    }
  };

  const displayPage = pageMode ? (currentPage || 1) : 0;

  // Page mode: show only current page
  if (pageMode) {
    return (
      <div className="flex items-center justify-center h-full w-full" onMouseUp={handleTextSelect}>
        <div className="page-flip-enter" key={displayPage}>
          {preloaded.has(displayPage) ? (
            <img
              src={`/api/reader/${bookId}/page/${displayPage - 1}`}
              alt={`Page ${displayPage}`}
              className="pdf-page rounded shadow-lg"
              style={{ maxWidth: '800px', maxHeight: '90vh', objectFit: 'contain' }}
            />
          ) : (
            <div className="skeleton rounded" style={{ width: '800px', height: '1000px' }} />
          )}
          <div className="text-center text-xs text-gray-400 py-2">{displayPage} / {totalPages}</div>
        </div>
      </div>
    );
  }

  // Scroll mode: show all pages
  const pageElements = [];
  const startPage = Math.max(1, displayPage > 0 ? displayPage - 2 : 1);
  const endPage = Math.min(totalPages, displayPage > 0 ? displayPage + 3 : 5);

  for (let i = startPage; i <= endPage; i++) {
    pageElements.push(
      <div
        key={i}
        ref={(el) => { if (el) pageRefs.current.set(i, el); }}
        data-page={i}
        className="pdf-page"
        style={{ width: '800px', minHeight: '100px' }}
      >
        <img
          src={`/api/reader/${bookId}/page/${i - 1}`}
          alt={`Page ${i}`}
          style={{ width: '100%', display: 'block' }}
          loading="lazy"
        />
        <div className="text-center text-xs text-gray-400 py-2">{i}</div>
      </div>
    );
  }

  return (
    <div className="pdf-container" ref={containerRef} onMouseUp={handleTextSelect}>
      <div className="flex flex-col items-center py-4">
        {displayPage > 5 && (
          <div className="text-center text-xs text-gray-400 py-4">... 向前翻页浏览更多 ...</div>
        )}
        {pageElements}
        {endPage < totalPages && (
          <div className="text-center text-xs text-gray-400 py-4">... 继续滚动浏览更多 ...</div>
        )}
      </div>
    </div>
  );
}
