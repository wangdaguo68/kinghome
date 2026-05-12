import { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getBook, getBookContent, updateProgress, getBookToc } from '../api';
import EpubReader from '../components/EpubReader';
import PdfReader from '../components/PdfReader';
import HighlightsPanel from '../components/HighlightsPanel';

type Theme = 'white' | 'beige' | 'green' | 'dark';
const THEME_CLASSES: Record<Theme, string> = {
  white: 'theme-white', beige: 'theme-beige', green: 'theme-green', dark: 'theme-dark',
};
const THEME_LABELS: Record<Theme, string> = { white: '白色', beige: '米黄', green: '护眼', dark: '夜间' };
const FONT_SIZES = [14, 16, 18, 20, 22, 24];
const LINE_HEIGHTS = [1.6, 1.8, 2.0, 2.2];
const MARGINS: { label: string; value: number }[] = [
  { label: '窄', value: 500 }, { label: '中', value: 750 }, { label: '宽', value: 1000 },
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
  const [fullscreen, setFullscreen] = useState(false);
  const [topBarHidden, setTopBarHidden] = useState(false);

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const secondsRef = useRef(0);
  const lastScrollY = useRef(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!bookId) return;
    setLoadError('');
    setBook(null);
    setContent(null);
    getBook(+bookId).then(r => setBook(r.data)).catch(e => setLoadError('Failed to load book info'));
    getBookContent(+bookId).then(r => setContent(r.data)).catch(e => setLoadError('Failed to load book content: ' + (e.response?.data?.detail || e.message)));
    getBookToc(+bookId).then(r => setToc(r.data.toc || [])).catch(() => {});
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

  const handleProgress = useCallback((p: any) => {
    setProgress(p);
    if (bookId) {
      updateProgress(+bookId, {
        current_page: p.currentPage, total_pages: p.totalPages, progress_percent: p.percent,
        current_chapter: p.chapter, reading_seconds_delta: secondsRef.current,
      }).catch(() => {});
      secondsRef.current = 0;
    }
  }, [bookId]);

  // Auto-hide top bar on scroll
  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const currentScrollY = container.scrollTop;
    if (currentScrollY > lastScrollY.current && currentScrollY > 80) {
      setTopBarHidden(true);
    } else if (currentScrollY < lastScrollY.current) {
      setTopBarHidden(false);
    }
    lastScrollY.current = currentScrollY;
  }, []);

  const toggleFullscreen = () => {
    if (!fullscreen) {
      document.documentElement.requestFullscreen?.();
      setFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setFullscreen(false);
    }
  };

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

  if (!book || !content) {
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
    maxWidth: `${marginWidth}px`,
  };

  return (
    <div className={`flex flex-col h-screen ${THEME_CLASSES[theme]}`}>
      {/* Top bar */}
      <div className={`reader-bar dark:bg-gray-800 dark:border-gray-700 ${topBarHidden ? 'hidden' : ''}`}>
        <button onClick={() => navigate('/')} className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400">
          ← 返回
        </button>
        <span className="text-sm font-medium truncate max-w-xs">{book.title}</span>
        <div className="flex items-center gap-4">
          <button onClick={toggleFullscreen} className="text-sm text-gray-400 hover:text-gray-600" title="全屏">
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
        <div ref={scrollContainerRef} onScroll={handleScroll}
          className="epub-view" style={readerStyle}>
          {content.format === 'pdf' ? (
            <PdfReader bookId={+bookId!} book={book} onProgress={handleProgress} />
          ) : (
            <EpubReader bookId={+bookId!} book={book} onProgress={handleProgress} theme={theme} fontSize={fontSize} lineHeight={lineHeight} marginWidth={marginWidth} />
          )}
        </div>

        {/* TOC sidebar */}
        {showToc && (
          <div className="absolute right-0 top-0 w-72 h-full bg-white dark:bg-gray-800 shadow-xl border-l border-gray-200 dark:border-gray-700 overflow-y-auto z-20 p-4" style={{ animation: 'slideUp 0.2s ease' } as any}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium">目录</h3>
              <button onClick={() => setShowToc(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            {toc.map((item: any, i: number) => (
              <div key={i} className="text-sm py-1.5 cursor-pointer hover:text-green-500 truncate"
                style={{ paddingLeft: (item.level || 0) * 16 }}
                onClick={() => setShowToc(false)}>
                {item.title}
              </div>
            ))}
            {toc.length === 0 && <p className="text-sm text-gray-400">暂无目录</p>}
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
      <div className="reader-bottom-bar dark:bg-gray-800 dark:border-gray-700">
        <span className="truncate max-w-[40%]">{progress.chapter || ''}</span>
        <span>{progress.currentPage} / {progress.totalPages} · {Math.round(progress.percent)}%</span>
      </div>

      {/* Settings overlay */}
      {showSettings && (
        <div className="reader-settings-overlay" onClick={() => setShowSettings(false)}>
          <div className="reader-settings-panel" onClick={e => e.stopPropagation()}>
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
            <div>
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
          </div>
        </div>
      )}
    </div>
  );
}
