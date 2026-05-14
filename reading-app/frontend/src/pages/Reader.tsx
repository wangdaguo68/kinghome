import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getBook, getBookContent, updateProgress, getBookToc } from '../api';
import HtmlEpubReader from '../components/HtmlEpubReader';
import PdfReader from '../components/PdfReader';
import HighlightsPanel from '../components/HighlightsPanel';

type ReadingMode = 'scroll' | 'page';

const FONT_SIZES = [14, 16, 18, 20, 22, 24];
const LINE_HEIGHTS = [1.6, 1.8, 2.0, 2.2];
const MARGINS: { label: string; value: number }[] = [
  { label: '窄', value: 500 }, { label: '中', value: 750 }, { label: '宽', value: 1000 },
];
const AUTO_FLIP_SPEEDS = [5, 10, 30, 60, 120];
const BREAK_INTERVALS = [20, 30, 45, 60];

function loadBookmarks(bookId: number) {
  try {
    const raw = localStorage.getItem(`bookmarks_${bookId}`);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}
function saveBookmarks(bookId: number, bm: any[]) {
  localStorage.setItem(`bookmarks_${bookId}`, JSON.stringify(bm));
}

const SHORTCUTS = [
  { keys: '← →', desc: '上一页/下一页' },
  { keys: 'Space', desc: '下一页' },
  { keys: 'F', desc: '全屏' },
  { keys: 'Esc', desc: '退出全屏/关闭' },
  { keys: 'M', desc: '切换阅读模式' },
  { keys: 'A', desc: '自动翻页' },
  { keys: '+ / -', desc: '放大/缩小字号' },
  { keys: 'B', desc: '添加书签' },
  { keys: 'G', desc: '跳转到页面' },
  { keys: '?', desc: '显示快捷键' },
];

export default function Reader() {
  const { bookId } = useParams<{ bookId: string }>();
  const navigate = useNavigate();
  const [book, setBook] = useState<any>(null);
  const [content, setContent] = useState<any>(null);
  const [loadError, setLoadError] = useState('');
  const [toc, setToc] = useState<any[]>([]);
  const [showToc, setShowToc] = useState(false);
  const [showHighlights, setShowHighlights] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [progress, setProgress] = useState({ currentPage: 0, totalPages: 0, percent: 0, chapter: '' });

  const [fontSize, setFontSize] = useState(16);
  const [lineHeight, setLineHeight] = useState(1.9);
  const [marginWidth, setMarginWidth] = useState(750);

  const [readingMode, setReadingMode] = useState<ReadingMode>('scroll');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [autoFlip, setAutoFlip] = useState({ enabled: false, speed: 10 });

  const [blueLight, setBlueLight] = useState(0);
  const [breakReminder, setBreakReminder] = useState({ enabled: false, interval: 30 });
  const [focusMode, setFocusMode] = useState(false);

  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showGoToPage, setShowGoToPage] = useState(false);
  const [goToPageInput, setGoToPageInput] = useState('');
  const [bookmarks, setBookmarks] = useState<any[]>([]);
  const [breakActive, setBreakActive] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const secondsRef = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const breakTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoFlipTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [format, setFormat] = useState<string>('');

  // Load book info
  useEffect(() => {
    if (!bookId) return;
    setLoadError('');
    setBook(null);
    setContent(null);
    const id = +bookId;

    getBook(id).then(r => {
      setBook(r.data);
      setFormat((r.data.format || '').toLowerCase());
    }).catch(() => setLoadError('Failed to load book info'));

    getBookContent(id).then(r => {
      const data = r.data;
      setContent(data);
      if (data.total_pages) setTotalPages(data.total_pages);
      if (data.total_chapters) setTotalPages(data.total_chapters);
    }).catch((e: any) => {
      setLoadError('Failed to load book content: ' + (e?.message || e?.response?.status || 'Unknown error'));
    });

    getBookToc(id).then(r => setToc(r.data.toc || [])).catch(() => {});
    setBookmarks(loadBookmarks(id));
  }, [bookId]);

  // Reading time tracking
  useEffect(() => {
    timerRef.current = setInterval(() => { secondsRef.current++; }, 1000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [bookId]);

  // Periodic progress save
  useEffect(() => {
    const saveInterval = setInterval(() => {
      if (secondsRef.current > 0 && bookId) {
        updateProgress(+bookId, { reading_seconds_delta: secondsRef.current }).catch(() => {});
        secondsRef.current = 0;
      }
    }, 30000);
    return () => clearInterval(saveInterval);
  }, [bookId]);

  // Save on exit
  useEffect(() => {
    const save = () => { if (bookId) updateProgress(+bookId, { reading_seconds_delta: secondsRef.current }).catch(() => {}); };
    window.addEventListener('beforeunload', save);
    return () => { window.removeEventListener('beforeunload', save); save(); };
  }, [bookId]);

  // Break reminder timer
  useEffect(() => {
    if (breakReminder.enabled && !breakActive) {
      breakTimerRef.current = setInterval(() => setBreakActive(true), breakReminder.interval * 60 * 1000);
    } else {
      if (breakTimerRef.current) clearInterval(breakTimerRef.current);
    }
    return () => { if (breakTimerRef.current) clearInterval(breakTimerRef.current); };
  }, [breakReminder.enabled, breakReminder.interval, breakActive]);

  // Auto-flip timer
  useEffect(() => {
    if (autoFlip.enabled && readingMode !== 'scroll') {
      autoFlipTimerRef.current = setInterval(() => {
        setCurrentPage(p => {
          if (p < totalPages) {
            handleProgress({ currentPage: p + 1, totalPages, percent: Math.round(((p + 1) / totalPages) * 100), chapter: progress.chapter });
            return p + 1;
          }
          setAutoFlip(f => ({ ...f, enabled: false }));
          return p;
        });
      }, autoFlip.speed * 1000);
    } else {
      if (autoFlipTimerRef.current) clearInterval(autoFlipTimerRef.current);
    }
    return () => { if (autoFlipTimerRef.current) clearInterval(autoFlipTimerRef.current); };
  }, [autoFlip.enabled, autoFlip.speed, readingMode, totalPages]);

  const handleProgress = useCallback((p: any) => {
    setProgress(p);
    if (p.currentPage) setCurrentPage(p.currentPage);
    if (p.totalPages) setTotalPages(p.totalPages);
    if (bookId) {
      updateProgress(+bookId, {
        current_page: p.currentPage, total_pages: p.totalPages, progress_percent: p.percent,
        current_chapter: p.chapter, reading_seconds_delta: secondsRef.current,
      }).catch(() => {});
      secondsRef.current = 0;
    }
  }, [bookId]);

  const isEpub = format === 'epub';
  const isPdf = format === 'pdf';
  const isMobi = format === 'mobi';

  const scrollPage = useCallback((dir: 1 | -1) => {
    const container = scrollContainerRef.current;
    if (!container) return;
    if (isEpub) {
      const iframe = container.querySelector('iframe');
      if (iframe?.contentWindow) {
        iframe.contentWindow.scrollBy({ top: dir * iframe.contentWindow.innerHeight * 0.8, behavior: 'smooth' });
      }
      return;
    }
    if (isPdf) {
      // PdfReader renders its own .pdf-container inside the outer one — scroll the inner
      const inner = container.querySelector('.pdf-container') as HTMLElement | null;
      (inner || container).scrollBy({ top: dir * (inner || container).clientHeight * 0.8, behavior: 'smooth' });
      return;
    }
    container.scrollBy({ top: dir * container.clientHeight * 0.8, behavior: 'smooth' });
  }, [isEpub, isPdf]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (readingMode === 'scroll') { scrollPage(1); }
        else if (totalPages > 0) { setCurrentPage(p => Math.min(p + 1, totalPages)); }
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (readingMode === 'scroll') { scrollPage(-1); }
        else if (totalPages > 0) { setCurrentPage(p => Math.max(p - 1, 1)); }
      } else if (e.key === ' ') {
        e.preventDefault();
        if (readingMode === 'scroll') { scrollPage(1); }
        else if (totalPages > 0) { setCurrentPage(p => Math.min(p + 1, totalPages)); }
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.key === 'Escape') {
        setShowSettings(false); setShowToc(false); setShowHighlights(false);
        setShowShortcuts(false); setShowGoToPage(false); setBreakActive(false);
        setFocusMode(false);
        if (document.fullscreenElement) document.exitFullscreen?.();
      } else if (e.key === 'm' || e.key === 'M') {
        setReadingMode(m => m === 'scroll' ? 'page' : 'scroll');
      } else if (e.key === 'a' || e.key === 'A') {
        setAutoFlip(f => ({ ...f, enabled: !f.enabled }));
      } else if (e.key === 'b' || e.key === 'B') {
        addBookmark();
      } else if (e.key === 'g' || e.key === 'G') {
        setShowGoToPage(true);
        setGoToPageInput('');
      } else if (e.key === '?') {
        setShowShortcuts(v => !v);
      } else if (e.key === '=' || e.key === '+') {
        setFontSize(s => Math.min(s + 2, 24));
      } else if (e.key === '-') {
        setFontSize(s => Math.max(s - 2, 14));
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [readingMode, totalPages, bookId, scrollPage]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
    else document.exitFullscreen?.();
  };

  const addBookmark = () => {
    const bm = { page: progress.currentPage || currentPage, chapter: progress.chapter, time: Date.now(), snippet: '' };
    const updated = [bm, ...bookmarks].slice(0, 50);
    setBookmarks(updated);
    if (bookId) saveBookmarks(+bookId, updated);
  };

  const goToPage = () => {
    const p = parseInt(goToPageInput);
    if (p >= 1 && p <= totalPages) {
      setCurrentPage(p);
      setShowGoToPage(false);
    }
  };

  // All formats need content before rendering
  const canRender = book && content && (isEpub || isPdf || isMobi);

  if (loadError) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-4">加载失败</p>
          <p className="text-sm mb-6 text-(--color-text-secondary)">{loadError}</p>
          <button onClick={() => navigate('/')} className="px-4 py-2 bg-(--color-primary) text-(--color-bg) rounded-lg text-sm font-medium">返回书架</button>
        </div>
      </div>
    );
  }

  if (!canRender) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="skeleton w-16 h-16 rounded-full mx-auto mb-4" />
          <div className="skeleton h-5 w-48 mx-auto mb-2" />
          <div className="skeleton h-3 w-32 mx-auto" />
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-screen ${focusMode ? 'reader-focus' : ''}`}
      style={blueLight > 0 ? { filter: `sepia(${blueLight * 0.3}%) hue-rotate(${-blueLight * 0.5}deg)` } : undefined}>

      {/* Top bar */}
      <div className={`reader-bar ${focusMode ? 'reader-bar-auto' : ''}`}>
        <button onClick={() => navigate('/')} className="text-sm text-(--color-text-secondary) hover:text-(--color-text) transition-colors">
          ← 返回
        </button>
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium truncate max-w-[200px] text-(--color-text)">{book?.title}</span>
          <div className="flex items-center gap-0.5 bg-(--color-bg) rounded-lg p-0.5 border border-(--color-border)">
            {(['scroll', 'page'] as ReadingMode[]).map(mode => (
              <button key={mode} onClick={() => setReadingMode(mode)}
                className={`px-2 py-1 rounded text-xs transition-colors ${readingMode === mode ? 'bg-(--color-card-raised) text-(--color-primary) font-medium border border-(--color-border)' : 'text-(--color-text-secondary) hover:text-(--color-text)'}`}>
                {mode === 'scroll' ? '滚动' : '单页'}
              </button>
            ))}
          </div>
          {readingMode !== 'scroll' && (
            <button onClick={() => setAutoFlip(f => ({ ...f, enabled: !f.enabled }))}
              className={`text-xs px-2 py-1 rounded transition-colors ${autoFlip.enabled ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)'}`}>
              {autoFlip.enabled ? `自动 ${autoFlip.speed}s` : '自动'}
            </button>
          )}
          <button onClick={toggleFullscreen} className="text-sm text-(--color-text-secondary) hover:text-(--color-text) transition-colors" title="全屏 (F)">⛶</button>
          <button onClick={() => setShowHighlights(!showHighlights)} className="text-sm text-(--color-text-secondary) hover:text-(--color-text) transition-colors">笔记</button>
          <button onClick={() => setShowToc(!showToc)} className="text-sm text-(--color-text-secondary) hover:text-(--color-text) transition-colors">目录</button>
          <button onClick={() => setShowSettings(!showSettings)} className="text-sm text-(--color-text-secondary) hover:text-(--color-text) transition-colors">Aa</button>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 relative overflow-hidden">
        {readingMode !== 'scroll' && totalPages > 0 && (
          <>
            <button className="absolute left-0 top-0 w-[25%] h-full z-10 cursor-pointer opacity-0 hover:opacity-100 transition-opacity"
              onClick={() => setCurrentPage(p => Math.max(p - 1, 1))} title="上一页 (←)" />
            <button className="absolute right-0 top-0 w-[25%] h-full z-10 cursor-pointer opacity-0 hover:opacity-100 transition-opacity"
              onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))} title="下一页 (→)" />
            <button onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
              className="absolute left-4 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center text-lg transition-colors"
              style={{ background: 'rgba(44,31,15,0.88)', backdropFilter: 'blur(12px)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
              title="上一页">‹</button>
            <button onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
              className="absolute right-4 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full flex items-center justify-center text-lg transition-colors"
              style={{ background: 'rgba(44,31,15,0.88)', backdropFilter: 'blur(12px)', border: '1px solid var(--color-border)', color: 'var(--color-text)' }}
              title="下一页">›</button>
          </>
        )}

        <div ref={scrollContainerRef}
          className={readingMode === 'scroll' ? (isEpub ? 'epub-view' : 'pdf-container') : 'reader-page-container'}>

          {isPdf ? (
            <PdfReader bookId={+bookId!} onProgress={handleProgress}
              pageMode={readingMode !== 'scroll'} currentPage={currentPage} onPageTotal={setTotalPages}
              totalPages={content?.total_pages || 0} />
          ) : (
            <HtmlEpubReader bookId={+bookId!} onProgress={handleProgress}
              fontSize={fontSize} lineHeight={lineHeight} marginWidth={marginWidth}
              isMobi={isMobi} mobiContent={isMobi ? content?.content : null}
              chapters={content?.chapters}
              pageMode={readingMode !== 'scroll'} currentPage={currentPage}
              onPageChange={setCurrentPage} onPageTotal={setTotalPages} />
          )}
        </div>

        {/* TOC sidebar */}
        {showToc && (
          <div className="absolute right-0 top-0 w-80 h-full shadow-xl border-l overflow-y-auto z-20"
            style={{ background: 'var(--color-card-raised)', borderColor: 'var(--color-border)', animation: 'slideUp 0.2s ease' } as any}>
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium text-(--color-text)">目录</h3>
                <button onClick={() => setShowToc(false)} className="text-(--color-text-secondary) hover:text-(--color-text)">✕</button>
              </div>
              {bookmarks.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-medium text-(--color-text-secondary) mb-2">书签 ({bookmarks.length})</p>
                  {bookmarks.map((bm: any, i: number) => (
                    <div key={i} className="text-sm py-1.5 cursor-pointer hover:text-(--color-primary) flex items-center gap-2 text-(--color-text)"
                      onClick={() => { setCurrentPage(bm.page); setReadingMode('page'); setShowToc(false); }}>
                      <span>🔖</span>
                      <span>第 {bm.page} 页</span>
                      <span className="text-xs text-(--color-text-secondary)">{new Date(bm.time).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs font-medium text-(--color-text-secondary) mb-2">章节</p>
              {toc.map((item: any, i: number) => (
                <div key={i} className="text-sm py-1.5 cursor-pointer hover:text-(--color-primary) truncate text-(--color-text)"
                  style={{ paddingLeft: (item.level || 0) * 16 }}
                  onClick={() => {
                    setShowToc(false);
                    if (isPdf && item.page !== undefined) {
                      setCurrentPage(item.page + 1);
                    } else if (isEpub && content?.chapters) {
                      // Match: try index first, then title, then href substring
                      let idx = -1;
                      const chs = content.chapters;
                      // 1) same position
                      if (i < chs.length) idx = i;
                      // 2) title match
                      if (idx < 0) {
                        idx = chs.findIndex((ch: any) =>
                          ch.title === item.title || item.title?.includes(ch.title) || ch.title?.includes(item.title));
                      }
                      // 3) href fragment match against chapter index
                      if (idx < 0 && item.href) {
                        const hrefBase = item.href.split('#')[0];
                        idx = chs.findIndex((_: any, ci: number) => ci === parseInt(hrefBase) || hrefBase.includes(String(ci)));
                      }
                      if (idx >= 0) {
                        if (readingMode === 'scroll') setReadingMode('page');
                        setCurrentPage(idx + 1);
                      }
                    }
                  }}>
                  {item.title}
                </div>
              ))}
              {toc.length === 0 && <p className="text-sm text-(--color-text-secondary)">暂无目录</p>}
            </div>
          </div>
        )}

        {/* Highlights sidebar */}
        {showHighlights && (
          <div className="absolute right-0 top-0 w-80 h-full shadow-xl border-l overflow-y-auto z-20"
            style={{ background: 'var(--color-card-raised)', borderColor: 'var(--color-border)', animation: 'slideUp 0.2s ease' } as any}>
            <HighlightsPanel bookId={+bookId!} onClose={() => setShowHighlights(false)} />
          </div>
        )}
      </div>

      {/* Bottom bar */}
      <div className={`reader-bottom-bar ${focusMode ? 'reader-bar-auto' : ''}`}>
        <span className="mr-4">{readingMode !== 'scroll' ? `${currentPage} / ${totalPages || '?'} 页` : ''}</span>
        <span className="truncate max-w-[40%]">{progress.chapter || ''}</span>
        <span className="ml-4">{progress.currentPage} / {progress.totalPages} · {Math.round(progress.percent)}%</span>
      </div>

      {/* Settings overlay */}
      {showSettings && (
        <div className="reader-settings-overlay" onClick={() => setShowSettings(false)}>
          <div className="reader-settings-panel" onClick={e => e.stopPropagation()}>
            {/* Reading mode */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3 text-(--color-text)">阅读模式</p>
              <div className="flex gap-2">
                {(['scroll', 'page'] as ReadingMode[]).map(mode => (
                  <button key={mode} onClick={() => setReadingMode(mode)}
                    className={`px-4 py-2 rounded-lg text-sm ${readingMode === mode ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)'}`}>
                    {mode === 'scroll' ? '滚动模式' : '单页翻页'}
                  </button>
                ))}
              </div>
            </div>

            {/* Auto-flip speed */}
            {readingMode !== 'scroll' && (
              <div className="mb-6">
                <p className="text-sm font-medium mb-3 text-(--color-text)">自动翻页速度 (秒/页)</p>
                <div className="flex gap-2">
                  {AUTO_FLIP_SPEEDS.map(s => (
                    <button key={s} onClick={() => setAutoFlip(f => ({ ...f, speed: s }))}
                      className={`px-3 py-1 rounded-lg text-sm ${autoFlip.speed === s ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)'}`}>
                      {s}s
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Font size */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3 text-(--color-text)">字号</p>
              <div className="flex items-center gap-1">
                <span className="text-xs text-(--color-text-secondary)">A</span>
                {FONT_SIZES.map(s => (
                  <button key={s} onClick={() => setFontSize(s)}
                    className={`px-2 py-1 rounded text-sm ${fontSize === s ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)'}`}>
                    {s}
                  </button>
                ))}
                <span className="text-lg font-bold text-(--color-text)">A</span>
              </div>
            </div>

            {/* Line height */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3 text-(--color-text)">行间距</p>
              <div className="flex gap-2">
                {LINE_HEIGHTS.map(lh => (
                  <button key={lh} onClick={() => setLineHeight(lh)}
                    className={`px-3 py-1 rounded text-sm ${lineHeight === lh ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)'}`}>
                    {lh}x
                  </button>
                ))}
              </div>
            </div>

            {/* Margin */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3 text-(--color-text)">页边距</p>
              <div className="flex gap-2">
                {MARGINS.map(m => (
                  <button key={m.value} onClick={() => setMarginWidth(m.value)}
                    className={`px-3 py-1 rounded text-sm ${marginWidth === m.value ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)'}`}>
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Blue light filter */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3 text-(--color-text)">蓝光过滤: {blueLight}%</p>
              <input type="range" min="0" max="100" value={blueLight} onChange={e => setBlueLight(+e.target.value)}
                className="w-full" style={{ accentColor: 'var(--color-primary)' }} />
            </div>

            {/* Break reminder */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3 text-(--color-text)">休息提醒</p>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm cursor-pointer text-(--color-text)">
                  <input type="checkbox" checked={breakReminder.enabled} onChange={e => setBreakReminder(b => ({ ...b, enabled: e.target.checked }))}
                    style={{ accentColor: 'var(--color-primary)' }} />
                  开启
                </label>
                {breakReminder.enabled && (
                  <select value={breakReminder.interval} onChange={e => setBreakReminder(b => ({ ...b, interval: +e.target.value }))}
                    className="text-sm border rounded px-2 py-1 bg-(--color-bg) border-(--color-border) text-(--color-text)">
                    {BREAK_INTERVALS.map(i => <option key={i} value={i}>每 {i} 分钟</option>)}
                  </select>
                )}
              </div>
            </div>

            {/* Focus mode */}
            <div>
              <button onClick={() => { setFocusMode(f => !f); setShowSettings(false); }}
                className={`w-full py-2 rounded-lg text-sm ${focusMode ? 'bg-(--color-primary) text-(--color-bg) font-medium' : 'bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)'}`}>
                {focusMode ? '退出专注模式' : '进入专注模式 (F)'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Break reminder overlay */}
      {breakActive && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => setBreakActive(false)}>
          <div className="rounded-2xl p-8 max-w-sm text-center shadow-2xl" style={{ background: 'var(--color-card-raised)', border: '1px solid var(--color-border)' }} onClick={e => e.stopPropagation()}>
            <p className="text-4xl mb-4">🕐</p>
            <p className="text-lg font-medium mb-2 text-(--color-text)">该休息一下了</p>
            <p className="text-sm text-(--color-text-secondary) mb-4">你已经连续阅读了 {breakReminder.interval} 分钟。<br/>看看远处，让眼睛休息 20 秒。</p>
            <button onClick={() => setBreakActive(false)}
              className="px-6 py-2 bg-(--color-primary) text-(--color-bg) rounded-lg text-sm font-medium">知道了</button>
          </div>
        </div>
      )}

      {/* Keyboard shortcuts overlay */}
      {showShortcuts && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => setShowShortcuts(false)}>
          <div className="rounded-2xl p-6 max-w-sm shadow-2xl" style={{ background: 'var(--color-card-raised)', border: '1px solid var(--color-border)' }} onClick={e => e.stopPropagation()}>
            <h3 className="font-medium mb-4 text-(--color-text)">键盘快捷键</h3>
            <div className="space-y-2">
              {SHORTCUTS.map(s => (
                <div key={s.keys} className="flex items-center justify-between text-sm">
                  <span className="text-(--color-text-secondary)">{s.desc}</span>
                  <kbd className="px-2 py-0.5 rounded text-xs font-mono bg-(--color-bg) text-(--color-text-secondary) border border-(--color-border)">{s.keys}</kbd>
                </div>
              ))}
            </div>
            <button onClick={() => setShowShortcuts(false)}
              className="mt-4 w-full py-2 rounded-lg text-sm bg-(--color-bg) text-(--color-text) border border-(--color-border)">关闭</button>
          </div>
        </div>
      )}

      {/* Go to page dialog */}
      {showGoToPage && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => setShowGoToPage(false)}>
          <div className="rounded-2xl p-6 shadow-2xl" style={{ background: 'var(--color-card-raised)', border: '1px solid var(--color-border)' }} onClick={e => e.stopPropagation()}>
            <h3 className="font-medium mb-3 text-(--color-text)">跳转到页面 (1 - {totalPages || '?'})</h3>
            <div className="flex gap-2">
              <input type="number" min={1} max={totalPages} value={goToPageInput}
                onChange={e => setGoToPageInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && goToPage()}
                className="settings-input w-32" autoFocus placeholder="页码" />
              <button onClick={goToPage} className="px-4 py-2 bg-(--color-primary) text-(--color-bg) rounded-lg text-sm font-medium">跳转</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
