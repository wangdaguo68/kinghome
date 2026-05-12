import { useEffect, useRef, useState } from 'react';
import { createHighlight } from '../api';

interface Props {
  bookId: number;
  book: any;
  onProgress: (p: { currentPage: number; totalPages: number; percent: number; chapter: string }) => void;
}

export default function PdfReader({ bookId, book, onProgress }: Props) {
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loadedPages, setLoadedPages] = useState<Set<number>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  useEffect(() => {
    // Get PDF metadata
    import('pdfjs-dist').then(async (pdfjs: any) => {
      pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.mjs';
      const doc = await pdfjs.getDocument(book.file_path).promise;
      setTotalPages(doc.numPages);
    });
  }, [book.file_path]);

  // Intersection observer to track current page
  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter(e => e.isIntersecting);
        if (visible.length > 0) {
          const pageEl = visible[0].target as HTMLElement;
          const page = parseInt(pageEl.dataset.page || '1');
          setCurrentPage(page);
          onProgress({
            currentPage: page,
            totalPages,
            percent: totalPages > 0 ? Math.round((page / totalPages) * 100) : 0,
            chapter: '',
          });
        }
      },
      { root: containerRef.current, threshold: 0.5 }
    );
    return () => observerRef.current?.disconnect();
  }, [totalPages]);

  // Lazy load visible pages
  useEffect(() => {
    const pagesToLoad = new Set<number>();
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 3); i++) {
      if (!loadedPages.has(i)) pagesToLoad.add(i);
    }
    if (pagesToLoad.size === 0) return;

    const loadPages = async () => {
      const newLoaded = new Set(loadedPages);
      await Promise.all(Array.from(pagesToLoad).map(async (_pageNum: number) => {
        try {
          newLoaded.add(_pageNum);
        } catch {}
      }));
      setLoadedPages(new Set(newLoaded));
    };
    loadPages();
  }, [currentPage, totalPages]);

  const handleTextSelect = () => {
    const selection = window.getSelection();
    const text = selection?.toString().trim();
    if (text && text.length > 5 && containerRef.current?.contains(selection?.anchorNode as Node)) {
      createHighlight({
        book_id: bookId,
        content: text,
        page: currentPage,
        color: 'yellow',
      }).catch(() => {});
    }
  };

  const pageElements = [];
  for (let i = 1; i <= totalPages; i++) {
    pageElements.push(
      <div
        key={i}
        ref={(el) => { if (el) pageRefs.current.set(i, el); }}
        data-page={i}
        className="pdf-page"
        style={{ width: '800px', minHeight: '100px' }}
      >
        <img
          src={loadedPages.has(i) ? `/api/reader/${bookId}/page/${i - 1}` : ''}
          alt={`Page ${i}`}
          style={{ width: '100%', display: loadedPages.has(i) ? 'block' : 'none' }}
          loading="lazy"
        />
        {!loadedPages.has(i) && (
          <div className="skeleton" style={{ width: '800px', height: '1100px' }} />
        )}
        <div className="text-center text-xs text-gray-400 py-2">{i}</div>
      </div>
    );
  }

  return (
    <div className="pdf-container" ref={containerRef} onMouseUp={handleTextSelect}>
      <div className="flex flex-col items-center py-4">
        {pageElements}
      </div>
    </div>
  );
}
