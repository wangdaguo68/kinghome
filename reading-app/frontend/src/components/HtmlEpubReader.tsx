import { useEffect, useRef, useState, useCallback } from 'react';

interface Chapter {
  index: number;
  title: string;
}

interface Props {
  bookId: number;
  onProgress: (p: { currentPage: number; totalPages: number; percent: number; chapter: string }) => void;
  onChapterList?: (chapters: Chapter[]) => void;
  fontSize: number;
  lineHeight: number;
  marginWidth: number;
  isMobi?: boolean;
  mobiContent?: string | null;
  pageMode?: boolean;
  currentPage?: number;
  onPageChange?: (page: number) => void;
  onPageTotal?: (total: number) => void;
  chapters?: Chapter[];
}

export default function HtmlEpubReader({
  bookId, onProgress, onChapterList, fontSize, lineHeight,
  marginWidth, isMobi, mobiContent, pageMode, currentPage, onPageChange, onPageTotal,
  chapters: externalChapters,
}: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const loadedIdxRef = useRef(-1);

  // Load chapter list (skip if chapters provided by parent)
  useEffect(() => {
    if (isMobi) {
      setChapters([{ index: 0, title: 'MOBI Content' }]);
      onPageTotal?.(1);
      onProgress({ currentPage: 1, totalPages: 1, percent: 0, chapter: '' });
      setLoading(false);
      return;
    }
    if (externalChapters && externalChapters.length > 0) {
      setChapters(externalChapters);
      onChapterList?.(externalChapters);
      onPageTotal?.(externalChapters.length);
      setCurrentIdx(0);
      onProgress({ currentPage: 1, totalPages: externalChapters.length, percent: 0, chapter: externalChapters[0]?.title || '' });
      setLoading(false);
      return;
    }
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
  }, [bookId, isMobi]);

  // Handle external page change
  useEffect(() => {
    if (isMobi) return;
    if (pageMode && currentPage !== undefined && chapters.length > 0) {
      const idx = currentPage - 1;
      if (idx >= 0 && idx < chapters.length && idx !== currentIdx) {
        setCurrentIdx(idx);
      }
    }
  }, [currentPage, pageMode, chapters.length, isMobi]);

  // Load EPUB chapter HTML into iframe
  useEffect(() => {
    if (isMobi || chapters.length === 0 || currentIdx >= chapters.length) return;
    if (currentIdx === loadedIdxRef.current) return;

    const idx = currentIdx;
    loadedIdxRef.current = idx;

    fetch(`/api/reader/${bookId}/chapter/${idx}`)
      .then(r => r.json())
      .then(data => {
        if (currentIdx !== idx) return;

        const html = data.html || '';
        const css = data.css || '';
        const title = data.title || `Chapter ${idx + 1}`;

        onProgress({
          currentPage: idx + 1,
          totalPages: chapters.length,
          percent: Math.round(((idx + 1) / chapters.length) * 100),
          chapter: title,
        });

        const iframe = iframeRef.current;
        if (!iframe || !iframe.contentDocument) return;

        const doc = iframe.contentDocument;
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
                background: #FBF6ED;
                color: #3E3232;
                padding: 48px 56px;
                max-width: ${marginWidth}px;
                margin: 0 auto;
                font-family: Georgia, "Songti SC", "Noto Serif SC", "STSong", serif;
                transition: background 0.3s, color 0.3s;
              }
              h1, h2, h3, h4 { font-family: "Songti SC", "KaiTi", serif; margin: 0.8em 0 0.4em; }
              p { margin: 0.8em 0; text-indent: 2em; }
              a { color: #8B7355; }
              img { max-width: 100%; height: auto; border-radius: 4px; }
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
  }, [bookId, currentIdx, chapters.length, fontSize, lineHeight, marginWidth, isMobi]);

  // Render MOBI content
  useEffect(() => {
    if (!isMobi || !mobiContent) return;
    const iframe = iframeRef.current;
    if (!iframe || !iframe.contentDocument) return;
    const doc = iframe.contentDocument;
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
            background: #FBF6ED;
            color: #3E3232;
            padding: 48px 56px;
            max-width: ${marginWidth}px;
            margin: 0 auto;
            font-family: Georgia, "Songti SC", "Noto Serif SC", "STSong", serif;
          }
          pre { white-space: pre-wrap; font-family: inherit; margin: 0; }
        </style>
      </head>
      <body><pre>${mobiContent}</pre></body>
      </html>
    `);
    doc.close();
  }, [isMobi, mobiContent, fontSize, lineHeight, marginWidth]);

  // Apply setting changes without reloading
  useEffect(() => {
    if (isMobi && !mobiContent) return;
    const iframe = iframeRef.current;
    if (!iframe?.contentDocument?.body) return;
    const body = iframe.contentDocument.body;
    body.style.fontSize = `${fontSize}px`;
    body.style.lineHeight = String(lineHeight);
    body.style.maxWidth = `${marginWidth}px`;
  }, [fontSize, lineHeight, marginWidth, isMobi, mobiContent]);

  const goToChapter = useCallback((idx: number) => {
    if (idx >= 0 && idx < chapters.length) {
      setCurrentIdx(idx);
      onPageChange?.(idx + 1);
    }
  }, [chapters.length, onPageChange]);

  if (loading) {
    return <div className="flex items-center justify-center h-full text-(--color-text-secondary)">加载中...</div>;
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-red-400 mb-2">加载失败</p>
          <p className="text-xs text-(--color-text-secondary)">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-hidden relative">
        <iframe
          ref={iframeRef}
          className="w-full h-full border-none"
          title="Book Content"
          sandbox="allow-same-origin"
        />
        {!isMobi && (
          <div className="reader-page-nav">
            <button onClick={() => goToChapter(currentIdx - 1)} disabled={currentIdx <= 0}>‹</button>
            <span className="page-indicator">{currentIdx + 1} / {chapters.length}</span>
            <button onClick={() => goToChapter(currentIdx + 1)} disabled={currentIdx >= chapters.length - 1}>›</button>
          </div>
        )}
      </div>
    </div>
  );
}
