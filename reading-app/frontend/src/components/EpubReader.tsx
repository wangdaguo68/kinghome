import { useEffect, useRef, useState } from 'react';
import { createHighlight } from '../api';

interface Props {
  bookId: number;
  book: any;
  onProgress: (p: { currentPage: number; totalPages: number; percent: number; chapter: string }) => void;
  theme: string;
  fontSize: number;
  lineHeight: number;
  marginWidth: number;
}

export default function EpubReader({ bookId, book, onProgress, theme, fontSize, lineHeight, marginWidth }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [chapters, setChapters] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const renditionRef = useRef<any>(null);

  useEffect(() => {
    let cancelled = false;
    import('epubjs').then((epubjs) => {
      if (cancelled) return;
      const bookEpub = epubjs.default(book.file_path);
      const rendition = bookEpub.renderTo(containerRef.current!, {
        width: '100%',
        height: '100%',
        spread: 'none',
        flow: 'paginated',
      });
      renditionRef.current = rendition;
      rendition.display();

      bookEpub.ready.then(() => {
        if (cancelled) return;
        setLoading(false);
        bookEpub.loaded.navigation.then((nav: any) => {
          const toc = nav.toc || [];
          setChapters(toc.map((t: any, i: number) => ({
            index: i, title: t.label || `Chapter ${i + 1}`, href: t.href || '',
          })));
        });
        return bookEpub.locations.generate(800);
      }).then((locations: any) => {
        if (cancelled) return;
        rendition.on('relocated', (loc: any) => {
          const current = loc.start?.displayed?.page || 1;
          const total = locations.total || 1;
          const percent = Math.round((current / total) * 100);
          const chap = loc.start?.index || 0;
          onProgress({ currentPage: current, totalPages: total, percent, chapter: chapters[chap]?.title || '' });
        });
      });

      rendition.on('selected', (_cfiRange: string, contents: any) => {
        const selection = contents.window.getSelection();
        const text = selection?.toString().trim();
        if (text && text.length > 5) {
          const range = selection!.getRangeAt(0);
          const rect = range.getBoundingClientRect();
          showHighlightTooltip(rect, text, _cfiRange);
        }
      });

      return () => { if (!cancelled) bookEpub.destroy(); };
    });
    return () => { cancelled = true; };
  }, [book.file_path]);

  // Apply theme to epub iframe when theme changes
  useEffect(() => {
    const iframe = containerRef.current?.querySelector('iframe');
    if (iframe && iframe.contentDocument) {
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

  const showHighlightTooltip = (rect: DOMRect, text: string, cfi: string) => {
    const existing = document.querySelector('.highlight-tooltip');
    if (existing) existing.remove();

    const tooltip = document.createElement('div');
    tooltip.className = 'highlight-tooltip';
    tooltip.style.cssText = `
      position: fixed; top: ${rect.top - 45}px; left: ${rect.left + rect.width / 2}px;
      transform: translateX(-50%); background: #333; color: white; padding: 6px 12px;
      border-radius: 20px; font-size: 13px; z-index: 1000; cursor: pointer;
      display: flex; gap: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    `;
    const colors = [
      { name: '黄', value: 'yellow', bg: '#ffc107' },
      { name: '绿', value: 'green', bg: '#07c160' },
      { name: '蓝', value: 'blue', bg: '#2196f3' },
      { name: '红', value: 'red', bg: '#f44336' },
    ];
    colors.forEach(c => {
      const dot = document.createElement('span');
      dot.style.cssText = `display:inline-block;width:20px;height:20px;border-radius:50%;background:${c.bg};cursor:pointer;`;
      dot.title = c.name;
      dot.onclick = async (e) => {
        e.stopPropagation();
        try { await createHighlight({ book_id: bookId, content: text, cfi, color: c.value }); } catch {}
        tooltip.remove();
      };
      tooltip.appendChild(dot);
    });
    document.body.appendChild(tooltip);
    setTimeout(() => { if (document.body.contains(tooltip)) tooltip.remove(); }, 8000);
  };

  return (
    <div ref={containerRef} className="epub-container" style={{ maxWidth: `${marginWidth}px`, margin: '0 auto' }}>
      {loading && <div className="flex items-center justify-center h-full text-gray-400">加载中...</div>}
    </div>
  );
}
