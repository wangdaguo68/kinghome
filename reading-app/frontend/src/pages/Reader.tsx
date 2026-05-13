import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getBook, getBookContent, updateProgress, getBookToc } from '../api';
import HtmlEpubReader from '../components/HtmlEpubReader';
import PdfReader from '../components/PdfReader';
import HighlightsPanel from '../components/HighlightsPanel';

type Theme = 'white' | 'beige' | 'green' | 'dark';
type ReadingMode = 'scroll' | 'page' | 'double';

const THEME_CLASSES: Record<Theme, string> = {
  white: 'theme-white', beige: 'theme-beige', green: 'theme-green', dark: 'theme-dark',
};
const THEME_LABELS: Record<Theme, string> = { white: '白色', beige: '米黄', green: '护眼', dark: '夜间' };
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

  // Reading preferences
  const [theme, setTheme] = useState<Theme>('white');
  const [fontSize, setFontSize] = useState(16);
  const [lineHeight, setLineHeight] = useState(1.8);
  const [marginWidth, setMarginWidth] = useState(750);

  // New: reading modes
  const [readingMode, setReadingMode] = useState<ReadingMode>('scroll');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [autoFlip, setAutoFlip] = useState({ enabled: false, speed: 10 });

  // Eye protection
  const [blueLight, setBlueLight] = useState(0);
  const [breakReminder, setBreakReminder] = useState({ enabled: false, interval: 30 });
  const [focusMode, setFocusMode] = useState(false);

  // UI toggles
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [showGoToPage, setShowGoToPage] = useState(false);
  const [goToPageInput, setGoToPageInput] = useState('');
  const [bookmarks, setBookmarks] = useState<any[]>([]);
  const [breakActive, setBreakActive] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const secondsRef = useRef(0);
  const lastScrollY = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const breakTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const autoFlipTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const topBarTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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
    }).catch(e => setLoadError('Failed to load book info'));

    getBookContent(id).then(r => {
      const data = r.data;
      setContent(data);
      if (data.total_pages) setTotalPages(data.total_pages);
    }).catch(() => {}); // Non-fatal for EPUB

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
      breakTimerRef.current = setInterval(() => {
        setBreakActive(true);
      }, breakReminder.interval * 60 * 1000);
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

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (readingMode !== 'scroll') setCurrentPage(p => Math.min(p + 1, totalPages || p + 1));
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (readingMode !== 'scroll') setCurrentPage(p => Math.max(p - 1, 1));
      } else if (e.key === ' ') {
        e.preventDefault();
        if (readingMode !== 'scroll') setCurrentPage(p => Math.min(p + 1, totalPages || p + 1));
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.key === 'Escape') {
        setShowSettings(false); setShowToc(false); setShowHighlights(false);
        setShowShortcuts(false); setShowGoToPage(false); setBreakActive(false);
        setFocusMode(false);
        if (document.fullscreenElement) document.exitFullscreen?.();
      } else if (e.key === 'm' || e.key === 'M') {
        setReadingMode(m => m === 'scroll' ? 'page' : m === 'page' ? 'double' : 'scroll');
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
  }, [readingMode, totalPages, bookId]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.();
    } else {
      document.exitFullscreen?.();
    }
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

  // Determine if we have enough to render
  const isEpub = format === 'epub';
  const isPdf = format === 'pdf';
  const canRender = book && (isEpub || content); // EPUB can render without content, others need it

  if (loadError) {
    return (
      <div className="flex items-center justify-center h-screen text-gray-500">
        <div className="text-center">
          <p className="text-red-400 text-lg mb-4">加载失败</p>
          <p className="text-sm mb-6">{loadError}</p>
          <button onClick={() => navigate('/')} className="px-4 py-2 bg-green-500 text-white rounded-lg text-sm">返回书架</button>
        </div>
      </div>
    );
  }

  if (!canRender) {
    return (
      <div className="flex items-center justify-center h-screen text-gray-400">
        <div className="text-center">
          <div className="skeleton w-16 h-16 rounded-full mx-auto mb-4" />
          <div className="skeleton h-5 w-48 mx-auto mb-2" />
          <div className="skeleton h-3 w-32 mx-auto" />
        </div>
      </div>
    );
  }

  const readerStyle = {
    fontSize: `${fontSize}px`,
    lineHeight: lineHeight,
    maxWidth: readingMode === 'double' ? '1200px' : `${marginWidth}px`,
  };

  const blueLightStyle = blueLight > 0 ? {
    filter: `sepia(${blueLight * 0.3}%) hue-rotate(${-blueLight * 0.5}deg)`,
  } : {};

  return (
    <div className={`flex flex-col h-screen ${THEME_CLASSES[theme]} ${focusMode ? 'reader-focus' : ''}`} style={blueLightStyle}>
      {/* Top bar */}
      <div className={`reader-bar dark:bg-gray-800 dark:border-gray-700 ${focusMode ? 'reader-bar-auto' : ''}`}>
        <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400">
          ← 返回
        </button>
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium truncate max-w-[200px]">{book.title}</span>
          {/* Reading mode */}
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5">
            {(['scroll', 'page', 'double'] as ReadingMode[]).map(mode => (
              <button key={mode} onClick={() => setReadingMode(mode)}
                className={`px-2 py-1 rounded text-xs ${readingMode === mode ? 'bg-white dark:bg-gray-600 shadow-sm font-medium' : 'text-gray-500'}`}>
                {mode === 'scroll' ? '滚动' : mode === 'page' ? '单页' : '双页'}
              </button>
            ))}
          </div>
          {/* Auto-flip */}
          {readingMode !== 'scroll' && (
            <button onClick={() => setAutoFlip(f => ({ ...f, enabled: !f.enabled }))}
              className={`text-xs px-2 py-1 rounded ${autoFlip.enabled ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-500'}`}>
              {autoFlip.enabled ? `自动 ${autoFlip.speed}s` : '自动'}
            </button>
          )}
          <button onClick={toggleFullscreen} className="text-sm text-gray-400 hover:text-gray-600" title="全屏 (F)">
            ⛶
          </button>
          <button onClick={() => setShowHighlights(!showHighlights)} className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400">
            笔记
          </button>
          <button onClick={() => setShowToc(!showToc)} className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400">
            目录
          </button>
          <button onClick={() => setShowSettings(!showSettings)} className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400">
            Aa
          </button>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 relative overflow-hidden">
        {/* Page mode: click zones and navigation */}
        {readingMode !== 'scroll' && (
          <>
            <button className="absolute left-0 top-0 w-[30%] h-full z-10 cursor-pointer opacity-0 hover:opacity-100 transition-opacity"
              onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
              title="上一页 (←)" />
            <button className="absolute right-0 top-0 w-[70%] h-full z-10 cursor-pointer opacity-0 hover:opacity-100 transition-opacity"
              onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages || p + 1))}
              title="下一页 (→)" />
            {/* Page flip arrows */}
            <button onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
              className="absolute left-4 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-white/80 dark:bg-gray-800/80 shadow flex items-center justify-center text-lg hover:bg-white dark:hover:bg-gray-700 transition-colors"
              title="上一页">‹</button>
            <button onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages || p + 1))}
              className="absolute right-4 top-1/2 -translate-y-1/2 z-10 w-10 h-10 rounded-full bg-white/80 dark:bg-gray-800/80 shadow flex items-center justify-center text-lg hover:bg-white dark:hover:bg-gray-700 transition-colors"
              title="下一页">›</button>
          </>
        )}

        <div ref={scrollContainerRef}
          className={readingMode === 'scroll' ? 'epub-view' : 'reader-page-container'}
          style={readingMode === 'scroll' ? readerStyle : undefined}>
          {isPdf ? (
            <PdfReader bookId={+bookId!} book={book} onProgress={handleProgress}
              pageMode={readingMode !== 'scroll'} currentPage={currentPage} onPageTotal={setTotalPages} />
          ) : (
            <HtmlEpubReader bookId={+bookId!} onProgress={handleProgress} theme={theme}
              fontSize={fontSize} lineHeight={lineHeight} marginWidth={marginWidth}
              pageMode={readingMode !== 'scroll'} currentPage={currentPage}
              onPageChange={setCurrentPage} onPageTotal={setTotalPages} />
          )}
        </div>

        {/* TOC sidebar */}
        {showToc && (
          <div className="absolute right-0 top-0 w-80 h-full bg-white dark:bg-gray-800 shadow-xl border-l border-gray-200 dark:border-gray-700 overflow-y-auto z-20" style={{ animation: 'slideUp 0.2s ease' } as any}>
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-medium">目录</h3>
                <button onClick={() => setShowToc(false)} className="text-gray-400 hover:text-gray-600">✕</button>
              </div>
              {/* Bookmarks tab */}
              {bookmarks.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs font-medium text-gray-400 mb-2">书签 ({bookmarks.length})</p>
                  {bookmarks.map((bm: any, i: number) => (
                    <div key={i} className="text-sm py-1.5 cursor-pointer hover:text-green-500 flex items-center gap-2"
                      onClick={() => { setCurrentPage(bm.page); setReadingMode('page'); setShowToc(false); }}>
                      <span className="text-green-400">🔖</span>
                      <span>第 {bm.page} 页</span>
                      <span className="text-xs text-gray-400">{new Date(bm.time).toLocaleDateString()}</span>
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs font-medium text-gray-400 mb-2">章节</p>
              {toc.map((item: any, i: number) => (
                <div key={i} className="text-sm py-1.5 cursor-pointer hover:text-green-500 truncate"
                  style={{ paddingLeft: (item.level || 0) * 16 }}
                  onClick={() => setShowToc(false)}>
                  {item.title}
                </div>
              ))}
              {toc.length === 0 && <p className="text-sm text-gray-400">暂无目录</p>}
            </div>
          </div>
        )}

        {/* Highlights sidebar */}
        {showHighlights && (
          <div className="absolute right-0 top-0 w-80 h-full bg-white dark:bg-gray-800 shadow-xl border-l border-gray-200 dark:border-gray-700 overflow-y-auto z-20" style={{ animation: 'slideUp 0.2s ease' } as any}>
            <HighlightsPanel bookId={+bookId!} onClose={() => setShowHighlights(false)} />
          </div>
        )}
      </div>

      {/* Bottom bar */}
      <div className={`reader-bottom-bar dark:bg-gray-800 dark:border-gray-700 ${focusMode ? 'reader-bar-auto' : ''}`}>
        <span className="text-xs text-gray-400 mr-4">{
          readingMode !== 'scroll' ? `${currentPage} / ${totalPages || '?'} 页` : ''
        }</span>
        <span className="truncate max-w-[40%]">{progress.chapter || ''}</span>
        <span className="ml-4">{progress.currentPage} / {progress.totalPages} · {Math.round(progress.percent)}%</span>
      </div>

      {/* Settings overlay */}
      {showSettings && (
        <div className="reader-settings-overlay" onClick={() => setShowSettings(false)}>
          <div className="reader-settings-panel" onClick={e => e.stopPropagation()}>
            {/* Reading mode */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3">阅读模式</p>
              <div className="flex gap-2">
                {(['scroll', 'page', 'double'] as ReadingMode[]).map(mode => (
                  <button key={mode} onClick={() => setReadingMode(mode)}
                    className={`px-4 py-2 rounded-lg text-sm ${readingMode === mode ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                    {mode === 'scroll' ? '滚动模式' : mode === 'page' ? '单页翻页' : '双页模式'}
                  </button>
                ))}
              </div>
            </div>

            {/* Auto-flip speed */}
            {readingMode !== 'scroll' && (
              <div className="mb-6">
                <p className="text-sm font-medium mb-3">自动翻页速度 (秒/页)</p>
                <div className="flex gap-2">
                  {AUTO_FLIP_SPEEDS.map(s => (
                    <button key={s} onClick={() => setAutoFlip(f => ({ ...f, speed: s }))}
                      className={`px-3 py-1 rounded-lg text-sm ${autoFlip.speed === s ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                      {s}s
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Theme */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3">阅读主题</p>
              <div className="flex gap-3">
                {(Object.keys(THEME_CLASSES) as Theme[]).map(t => (
                  <button key={t} onClick={() => setTheme(t)}
                    className={`w-10 h-10 rounded-full border-2 transition-colors ${THEME_CLASSES[t]} ${theme === t ? 'border-green-500 ring-2 ring-green-200' : 'border-gray-200'}`}
                    title={THEME_LABELS[t]} />
                ))}
              </div>
            </div>

            {/* Font size */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3">字号</p>
              <div className="flex items-center gap-1">
                <span className="text-xs text-gray-400">A</span>
                {FONT_SIZES.map(s => (
                  <button key={s} onClick={() => setFontSize(s)}
                    className={`px-2 py-1 rounded text-sm ${fontSize === s ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                    {s}
                  </button>
                ))}
                <span className="text-lg font-bold">A</span>
              </div>
            </div>

            {/* Line height */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3">行间距</p>
              <div className="flex gap-2">
                {LINE_HEIGHTS.map(lh => (
                  <button key={lh} onClick={() => setLineHeight(lh)}
                    className={`px-3 py-1 rounded text-sm ${lineHeight === lh ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                    {lh}x
                  </button>
                ))}
              </div>
            </div>

            {/* Margin */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3">页边距</p>
              <div className="flex gap-2">
                {MARGINS.map(m => (
                  <button key={m.value} onClick={() => setMarginWidth(m.value)}
                    className={`px-3 py-1 rounded text-sm ${marginWidth === m.value ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Blue light filter */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3">蓝光过滤: {blueLight}%</p>
              <input type="range" min="0" max="100" value={blueLight} onChange={e => setBlueLight(+e.target.value)}
                className="w-full accent-green-500" />
            </div>

            {/* Break reminder */}
            <div className="mb-6">
              <p className="text-sm font-medium mb-3">休息提醒</p>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={breakReminder.enabled} onChange={e => setBreakReminder(b => ({ ...b, enabled: e.target.checked }))}
                    className="accent-green-500" />
                  开启
                </label>
                {breakReminder.enabled && (
                  <select value={breakReminder.interval} onChange={e => setBreakReminder(b => ({ ...b, interval: +e.target.value }))}
                    className="text-sm border rounded px-2 py-1 dark:bg-gray-700 dark:border-gray-600">
                    {BREAK_INTERVALS.map(i => (
                      <option key={i} value={i}>每 {i} 分钟</option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Focus mode */}
            <div>
              <button onClick={() => { setFocusMode(f => !f); setShowSettings(false); }}
                className={`w-full py-2 rounded-lg text-sm ${focusMode ? 'bg-green-500 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}>
                {focusMode ? '退出专注模式' : '进入专注模式 (F)'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Break reminder overlay */}
      {breakActive && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setBreakActive(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-sm text-center shadow-2xl" onClick={e => e.stopPropagation()}>
            <p className="text-4xl mb-4">🕐</p>
            <p className="text-lg font-medium mb-2">该休息一下了</p>
            <p className="text-sm text-gray-500 mb-4">你已经连续阅读了 {breakReminder.interval} 分钟。<br/>看看远处，让眼睛休息 20 秒。</p>
            <button onClick={() => setBreakActive(false)}
              className="px-6 py-2 bg-green-500 text-white rounded-lg text-sm">知道了</button>
          </div>
        </div>
      )}

      {/* Keyboard shortcuts overlay */}
      {showShortcuts && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setShowShortcuts(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 max-w-sm shadow-2xl" onClick={e => e.stopPropagation()}>
            <h3 className="font-medium mb-4">键盘快捷键</h3>
            <div className="space-y-2">
              {SHORTCUTS.map(s => (
                <div key={s.keys} className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">{s.desc}</span>
                  <kbd className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs font-mono">{s.keys}</kbd>
                </div>
              ))}
            </div>
            <button onClick={() => setShowShortcuts(false)}
              className="mt-4 w-full py-2 bg-gray-100 dark:bg-gray-700 rounded-lg text-sm">关闭</button>
          </div>
        </div>
      )}

      {/* Go to page dialog */}
      {showGoToPage && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center" onClick={() => setShowGoToPage(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-2xl" onClick={e => e.stopPropagation()}>
            <h3 className="font-medium mb-3">跳转到页面 (1 - {totalPages || '?'})</h3>
            <div className="flex gap-2">
              <input type="number" min={1} max={totalPages} value={goToPageInput}
                onChange={e => setGoToPageInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && goToPage()}
                className="settings-input w-32" autoFocus placeholder="页码" />
              <button onClick={goToPage} className="px-4 py-2 bg-green-500 text-white rounded-lg text-sm">跳转</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
