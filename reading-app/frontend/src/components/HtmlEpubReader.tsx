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

const _forwardedIframes = new WeakSet<HTMLIFrameElement>();
function forwardKeyboard(iframe: HTMLIFrameElement) {
  const win = iframe.contentWindow;
  if (!win || _forwardedIframes.has(iframe)) return;
  _forwardedIframes.add(iframe);
  win.addEventListener('keydown', (e: KeyboardEvent) => {
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', ' '].includes(e.key)) {
      e.preventDefault();
    }
    window.dispatchEvent(new KeyboardEvent('keydown', {
      key: e.key, code: e.code, ctrlKey: e.ctrlKey,
      shiftKey: e.shiftKey, altKey: e.altKey, metaKey: e.metaKey,
      repeat: e.repeat,
    }));
  });
}

export default function HtmlEpubReader({
  bookId, onProgress, onChapterList, fontSize, lineHeight,
  marginWidth, isMobi, mobiContent, currentPage, onPageChange, onPageTotal,
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
    // If chapters provided by parent, use them directly — don't re-fetch
    if (externalChapters !== undefined) {
      setChapters(externalChapters);
      onChapterList?.(externalChapters);
      onPageTotal?.(externalChapters.length);
      if (externalChapters.length > 0) {
        setCurrentIdx(0);
        onProgress({ currentPage: 1, totalPages: externalChapters.length, percent: 0, chapter: externalChapters[0]?.title || '' });
      }
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

  // Handle external page change (from Reader keyboard/TOC/page arrows)
  useEffect(() => {
    if (isMobi) return;
    if (currentPage !== undefined && chapters.length > 0) {
      const idx = currentPage - 1;
      if (idx >= 0 && idx < chapters.length && idx !== currentIdx) {
        setCurrentIdx(idx);
        onPageChange?.(idx + 1);
      }
    }
  }, [currentPage, chapters.length, isMobi]);

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
        // String concatenation safe against ${`} in user content
        doc.write(
          '<!DOCTYPE html><html><head><meta charset="utf-8"><style>' +
          'body{font-size:' + fontSize + 'px;line-height:' + lineHeight +
          ';background:#FBF6ED;color:#3E3232;padding:48px 56px;max-width:' + marginWidth +
          'px;margin:0 auto;font-family:Georgia,"Songti SC","Noto Serif SC","STSong",serif;transition:background 0.3s,color 0.3s}' +
          'h1,h2,h3,h4{font-family:"Songti SC","KaiTi",serif;margin:0.8em 0 0.4em}' +
          'p{margin:0.8em 0;text-indent:2em}a{color:#8B7355}' +
          'img{max-width:100%;height:auto;border-radius:4px}' +
          css +
          '</style></head><body>' + html + '</body></html>'
        );
        doc.close();

        forwardKeyboard(iframe);
      })
      .catch(e => {
        if (currentIdx === idx) {
          setError('Failed to load chapter: ' + (e.message || ''));
        }
      });
  }, [bookId, currentIdx, chapters.length, fontSize, lineHeight, marginWidth, isMobi]);

  const blobUrlRef = useRef<string | null>(null);

  // Render MOBI content via Blob URL (avoids srcdoc 2MB browser limit)
  useEffect(() => {
    if (!isMobi || !mobiContent) return;
    const iframe = iframeRef.current;
    if (!iframe) return;
    try {
      const html =
        '<!DOCTYPE html><html><head><meta charset="utf-8"><style id="mobi-base-style">' +
        'body{font-size:' + fontSize + 'px;line-height:' + lineHeight +
        ';background:#FBF6ED;color:#3E3232;padding:48px 56px;max-width:' + marginWidth +
        'px;margin:0 auto;font-family:Georgia,"Songti SC","Noto Serif SC","STSong",serif}' +
        'img{max-width:100%;height:auto;border-radius:4px}' +
        '</style></head><body>' + mobiContent + '</body></html>';
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);

      // Revoke previous blob URL to prevent memory leaks
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
      blobUrlRef.current = url;

      iframe.src = url;
      iframe.onload = () => { forwardKeyboard(iframe); };
    } catch (e: any) {
      setError('MOBI render failed: ' + e.message);
    }
  }, [isMobi, mobiContent, loading]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, []);

  // Apply setting changes without reloading (EPUB: body styles, MOBI: update <style>)
  useEffect(() => {
    if (isMobi && !mobiContent) return;
    const iframe = iframeRef.current;
    if (!iframe?.contentDocument) return;
    if (isMobi) {
      const styleEl = iframe.contentDocument.getElementById('mobi-base-style');
      if (styleEl) {
        styleEl.textContent =
          'body{font-size:' + fontSize + 'px;line-height:' + lineHeight +
          ';background:#FBF6ED;color:#3E3232;padding:48px 56px;max-width:' + marginWidth +
          'px;margin:0 auto;font-family:Georgia,"Songti SC","Noto Serif SC","STSong",serif}' +
          'img{max-width:100%;height:auto;border-radius:4px}';
      }
    }
    if (iframe.contentDocument.body) {
      const body = iframe.contentDocument.body;
      body.style.fontSize = String(fontSize) + 'px';
      body.style.lineHeight = String(lineHeight);
      body.style.maxWidth = String(marginWidth) + 'px';
    }
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

  if (chapters.length === 0 && !isMobi) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-(--color-text-secondary) mb-2">无法读取章节</p>
          <p className="text-xs text-(--color-text-secondary)">请检查文件是否完整</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex-1 overflow-hidden relative">
        <iframe
          ref={iframeRef}
          className="w-full h-full border-none"
          title="Book Content"
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
