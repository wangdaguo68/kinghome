import { useEffect, useRef, useState, useCallback } from 'react';

interface Chapter {
  index: number;
  title: string;
}

interface Props {
  bookId: number;
  onProgress: (p: { currentPage: number; totalPages: number; percent: number; chapter: string }) => void;
  onChapterList?: (chapters: Chapter[]) => void;
  theme: string;
  fontSize: number;
  lineHeight: number;
  marginWidth: number;
  pageMode?: boolean;
  currentPage?: number;
  onPageChange?: (page: number) => void;
  onPageTotal?: (total: number) => void;
}

export default function HtmlEpubReader({
  bookId, onProgress, onChapterList, theme, fontSize, lineHeight,
  marginWidth, pageMode, currentPage, onPageChange, onPageTotal,
}: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const loadedIdxRef = useRef(-1);

  // Load chapter list
  useEffect(() => {
    fetch(`/api/reader/${bookId}/content`)
      .then(r => r.json())
      .then(data => {
        const list = data.chapters || [];
        setChapters(list);
        onChapterList?.(list);
        onPageTotal?.(list.length);
        if (list.length > 0) {
          setCurrentIdx(0);
          onProgress({ currentPage: 1, totalPages: list.length, percent: 0, chapter: list[0]?.title || '' });
        }
        setLoading(false);
      })
      .catch(e => {
        setError('Failed to load chapter list: ' + (e.message || ''));
        setLoading(false);
      });
  }, [bookId]);

  // Handle external page change (from Reader.tsx keyboard/click handlers)
  useEffect(() => {
    if (pageMode && currentPage !== undefined && chapters.length > 0) {
      const idx = currentPage - 1;
      if (idx >= 0 && idx < chapters.length && idx !== currentIdx) {
        setCurrentIdx(idx);
      }
    }
  }, [currentPage, pageMode, chapters.length]);

  // Load chapter HTML into iframe
  useEffect(() => {
    if (chapters.length === 0 || currentIdx >= chapters.length) return;
    if (currentIdx === loadedIdxRef.current) return;

    const idx = currentIdx;
    loadedIdxRef.current = idx;

    fetch(`/api/reader/${bookId}/chapter/${idx}`)
      .then(r => r.json())
      .then(data => {
        // Ensure we're still on the same chapter
        if (currentIdx !== idx) return;

        const html = data.html || '';
        const css = data.css || '';
        const title = data.title || `Chapter ${idx + 1}`;

        // Update progress
        onProgress({
          currentPage: idx + 1,
          totalPages: chapters.length,
          percent: Math.round(((idx + 1) / chapters.length) * 100),
          chapter: title,
        });

        // Render in iframe
        const iframe = iframeRef.current;
        if (!iframe || !iframe.contentDocument) return;

        const doc = iframe.contentDocument;
        const bgMap: Record<string, string> = {
          white: '#FFFFFF', beige: '#FFF9E6', green: '#C7EDCC', dark: '#1A1A1A',
        };
        const colorMap: Record<string, string> = {
          white: '#1A1A1A', beige: '#3E3E3E', green: '#3E3E3E', dark: '#AAAAAA',
        };
        const bg = bgMap[theme] || '#FFFFFF';
        const color = colorMap[theme] || '#1A1A1A';

        doc.open();
        doc.write(`
          <!DOCTYPE html>
          <html>
          <head>
            <meta charset="utf-8">
            <style>
              body {
                font-size: ${fontSize}px;
                line-height: ${lineHeight};
                background: ${bg};
                color: ${color};
                padding: 32px;
                max-width: ${marginWidth}px;
                margin: 0 auto;
                font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
                transition: background 0.3s, color 0.3s;
              }
              img { max-width: 100%; height: auto; border-radius: 4px; }
              h1, h2, h3, h4 { margin: 0.8em 0 0.4em; }
              p { margin: 0.6em 0; }
              a { color: #07c160; }
              ${css}
            </style>
          </head>
          <body>${html}</body>
          </html>
        `);
        doc.close();
      })
      .catch(e => {
        if (currentIdx === idx) {
          setError('Failed to load chapter: ' + (e.message || ''));
        }
      });
  }, [bookId, currentIdx, chapters.length, theme, fontSize, lineHeight, marginWidth]);

  // Apply theme changes without reloading content
  useEffect(() => {
    const iframe = iframeRef.current;
    if (iframe?.contentDocument?.body) {
      const bgMap: Record<string, string> = {
        white: '#FFFFFF', beige: '#FFF9E6', green: '#C7EDCC', dark: '#1A1A1A',
      };
      const colorMap: Record<string, string> = {
        white: '#1A1A1A', beige: '#3E3E3E', green: '#3E3E3E', dark: '#AAAAAA',
      };
      iframe.contentDocument.body.style.background = bgMap[theme] || '#FFFFFF';
      iframe.contentDocument.body.style.color = colorMap[theme] || '#1A1A1A';
      iframe.contentDocument.body.style.fontSize = `${fontSize}px`;
      iframe.contentDocument.body.style.lineHeight = String(lineHeight);
    }
  }, [theme, fontSize, lineHeight]);

  const goToChapter = useCallback((idx: number) => {
    if (idx >= 0 && idx < chapters.length) {
      setCurrentIdx(idx);
      onPageChange?.(idx + 1);
    }
  }, [chapters.length, onPageChange]);

  if (loading) {
    return <div className="flex items-center justify-center h-full text-gray-400">加载中...</div>;
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        <div className="text-center">
          <p className="text-red-400 mb-2">加载失败</p>
          <p className="text-xs">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Content iframe */}
      <div className="flex-1 overflow-hidden relative">
        <iframe
          ref={iframeRef}
          className="w-full h-full border-none"
          title="Book Content"
          sandbox="allow-same-origin"
        />
        {/* Chapter nav overlay — shown in page mode or on hover */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-white/90 dark:bg-gray-800/90 rounded-full px-3 py-1.5 shadow-lg backdrop-blur text-xs">
          <button onClick={() => goToChapter(currentIdx - 1)} disabled={currentIdx <= 0}
            className="px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-default">
            ‹ 上一章
          </button>
          <span className="text-gray-500 min-w-[60px] text-center">
            {currentIdx + 1} / {chapters.length}
          </span>
          <button onClick={() => goToChapter(currentIdx + 1)} disabled={currentIdx >= chapters.length - 1}
            className="px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30 disabled:cursor-default">
            下一章 ›
          </button>
        </div>
      </div>
    </div>
  );
}
