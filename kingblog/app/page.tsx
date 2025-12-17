import Link from 'next/link';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { getPosts } from '@/lib/posts';

interface HomeProps {
  searchParams?: {
    date?: string;
    status?: string;
  };
}

export default async function Home({ searchParams }: HomeProps) {
  const date = searchParams?.date || '';
  const status = (searchParams?.status as 'draft' | 'published' | 'all') || 'published';

  const posts = await getPosts({
    status,
    date: date || undefined,
  });

  return (
    <div className="space-y-8">
      {/* 欢迎区域 */}
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          每日复盘
        </h1>
        <p className="text-lg text-gray-600 mb-8">
          记录每一天的思考与成长
        </p>
        <Link
          href="/posts/new"
          className="btn btn-primary inline-block"
        >
          写复盘
        </Link>
      </div>

      {/* 筛选区域 */}
      <div className="card space-y-4">
        <form method="get" className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-2">复盘日期</label>
            <input
              type="date"
              name="date"
              defaultValue={date}
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-2">状态</label>
            <select
              name="status"
              defaultValue={status}
              className="input"
            >
              <option value="published">已发布</option>
              <option value="draft">草稿</option>
              <option value="all">全部</option>
            </select>
          </div>
          <div className="flex items-end gap-3">
            <button type="submit" className="btn btn-primary">
              筛选
            </button>
            <Link href="/" className="btn btn-secondary">
              重置
            </Link>
          </div>
        </form>
        <div className="text-sm text-gray-500">
          {date ? `筛选日期：${date}` : '未按日期筛选'}
          {status !== 'published' ? `，状态：${status}` : ''}
        </div>
      </div>

      {/* 复盘列表 */}
      <div className="space-y-6">
        {posts.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-gray-500 mb-4">未找到复盘记录</p>
            <Link href="/posts/new" className="btn btn-primary">
              写一篇
            </Link>
          </div>
        ) : (
          posts.map((post: any) => (
            <article
              key={post.id}
              className="card hover:shadow-md transition-shadow duration-200"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <Link
                    href={`/posts/${post.id}`}
                    className="text-2xl font-semibold text-gray-900 hover:text-primary-600 transition-colors"
                  >
                    {post.title}
                  </Link>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                    <time>
                      {format(new Date(post.date), 'yyyy年MM月dd日', {
                        locale: zhCN,
                      })}
                    </time>
                    {post.mood && (
                      <span className="px-2 py-1 bg-primary-100 text-primary-700 rounded-full text-xs">
                        {post.mood}
                      </span>
                    )}
                    <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs">
                      {post.status === 'draft' ? '草稿' : '已发布'}
                    </span>
                  </div>
                </div>
              </div>

              {post.summary && (
                <div
                  className="text-gray-600 mb-4 line-clamp-2 prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{
                    __html: post.summary.replace(/<[^>]*>/g, '').substring(0, 200),
                  }}
                />
              )}

              <div className="flex items-center justify-between">
                <Link
                  href={`/posts/${post.id}`}
                  className="text-primary-600 hover:text-primary-700 font-medium"
                >
                  阅读全文 →
                </Link>
                <span className="text-sm text-gray-400">
                  {post.views} 次浏览
                </span>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}

