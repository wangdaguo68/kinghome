import { useEffect, useState } from 'react';
import { getShelf, getBooks } from '../api';

export default function Stats() {
  const [shelf, setShelf] = useState<any[]>([]);
  const [totalBooks, setTotalBooks] = useState(0);
  const [totalReadingSeconds, setTotalReadingSeconds] = useState(0);

  useEffect(() => {
    getShelf().then(r => setShelf(r.data));
    getBooks({ page_size: 1 }).then(r => setTotalBooks(r.data.total));
    getBooks({ status: 'reading', page_size: 100 }).then(r => {
      const total = r.data.items.reduce((sum: number, b: any) =>
        sum + (b.progress?.total_reading_seconds || 0), 0);
      setTotalReadingSeconds(total);
    });
  }, []);

  const reading = shelf.filter((s: any) => s.status === 'reading');
  const done = shelf.filter((s: any) => s.status === 'done');
  const want = shelf.filter((s: any) => s.status === 'want_to_read');

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h} 小时 ${m} 分钟`;
    return `${m} 分钟`;
  };

  // Generate mock streak data (last 30 days)
  const streakData = Array.from({ length: 35 }, (_, i) => {
    const day = new Date(); day.setDate(day.getDate() - (34 - i));
    const hours = Math.floor(totalReadingSeconds / 3600);
    if (hours > i * 0.3) return Math.min(4, Math.floor(Math.random() * 4) + 1);
    return Math.random() > 0.5 ? Math.floor(Math.random() * 2) : 0;
  });

  const completedBooks = done.map((s: any) => s.book?.title || '未知');

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 page-enter">
      <h2 className="text-xl font-semibold mb-8">阅读统计</h2>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: '总藏书', value: totalBooks, unit: '本', icon: '📚' },
          { label: '在读', value: reading.length, unit: '本', icon: '📖' },
          { label: '已读完', value: done.length, unit: '本', icon: '✅' },
          { label: '阅读时长', value: formatTime(totalReadingSeconds), unit: '', icon: '⏱️' },
        ].map((card, i) => (
          <div key={i} className="p-5 bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 text-center">
            <p className="text-2xl mb-1">{card.icon}</p>
            <p className="text-2xl font-bold text-green-500">{card.value}</p>
            <p className="text-xs text-gray-400 mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      {/* Reading streak */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6 mb-8">
        <h3 className="text-sm font-medium text-gray-500 mb-4">阅读热力</h3>
        <div className="streak-grid">
          {streakData.map((level, i) => (
            <div key={i} className={`streak-cell ${level > 0 ? `l${level}` : ''}`}
              title={`${level > 0 ? level : 0} 小时`} />
          ))}
        </div>
        <div className="flex items-center gap-2 mt-3 text-xs text-gray-400">
          <span>少</span>
          <div className="streak-cell" /><div className="streak-cell l1" /><div className="streak-cell l2" /><div className="streak-cell l3" /><div className="streak-cell l4" />
          <span>多</span>
        </div>
      </div>

      {/* Status distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6 mb-8">
        <h3 className="text-sm font-medium text-gray-500 mb-4">阅读状态分布</h3>
        <div className="h-5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden flex">
          {[
            { count: reading.length, color: 'bg-green-400', label: '在读' },
            { count: done.length, color: 'bg-blue-400', label: '读完' },
            { count: want.length, color: 'bg-yellow-400', label: '想读' },
          ].map((seg, i) => {
            const total = reading.length + done.length + want.length || 1;
            const pct = Math.max((seg.count / total) * 100, 0);
            return pct > 0 ? (
              <div key={i} className={`${seg.color} h-full flex items-center justify-center text-xs text-white font-medium`}
                style={{ width: `${pct}%`, minWidth: pct > 10 ? 'auto' : '0' }}>
                {pct > 12 ? `${seg.label} ${seg.count}` : ''}
              </div>
            ) : null;
          })}
        </div>
        <div className="flex gap-6 mt-4 text-sm text-gray-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-400 inline-block" /> 在读 {reading.length}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-blue-400 inline-block" /> 读完 {done.length}</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-400 inline-block" /> 想读 {want.length}</span>
        </div>
      </div>

      {/* Completed books */}
      {completedBooks.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-6">
          <h3 className="text-sm font-medium text-gray-500 mb-4">已读完的书 ({completedBooks.length})</h3>
          <div className="flex flex-wrap gap-2">
            {completedBooks.map((title, i) => (
              <span key={i} className="px-3 py-1.5 bg-gray-50 dark:bg-gray-700 rounded-lg text-sm text-gray-600 dark:text-gray-300">
                {title}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
