import Link from 'next/link';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { countPosts, getPosts } from '@/lib/posts';
import { getAllCategories } from '@/lib/categories';
import PostListWithActions from '@/components/PostListWithActions';

export const dynamic = 'force-dynamic';

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100, 500, 1000];

interface HomeProps {
  searchParams?: {
    date?: string;
    status?: string;
    categoryId?: string;
    page?: string;
    pageSize?: string;
  };
}

export default async function Home({ searchParams }: HomeProps) {
  const date = searchParams?.date || '';
  const status = (searchParams?.status as 'draft' | 'published' | 'all') || 'published';
  const categoryId = searchParams?.categoryId ? Number(searchParams.categoryId) : undefined;
  const pageParam = Number(searchParams?.page) || 1;
  const sizeParam = Number(searchParams?.pageSize) || 10;
  const pageSize = PAGE_SIZE_OPTIONS.includes(sizeParam) ? sizeParam : 10;
  const page = pageParam > 0 ? pageParam : 1;

  const [posts, categories, total] = await Promise.all([
    getPosts({
      status,
      date: date || undefined,
      categoryId,
      page,
      pageSize,
    }),
    getAllCategories(),
    countPosts({
      status,
      date: date || undefined,
      categoryId,
    }),
  ]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const buildPageHref = (targetPage: number) => {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    if (status) params.set('status', status);
    if (categoryId) params.set('categoryId', String(categoryId));
    params.set('page', String(targetPage));
    params.set('pageSize', String(pageSize));
    return `/?${params.toString()}`;
  };

  return (
    <div className="space-y-8">
      {/* 欢迎区域 */}
      <div className="text-center py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          每日笔记
        </h1>
        <p className="text-lg text-gray-600 mb-8">
          记录每一天的思考与成长
        </p>
        <Link
          href="/posts/new"
          className="btn btn-primary inline-block"
        >
          写笔记
        </Link>
      </div>

      {/* 筛选区域 */}
      <div className="card space-y-4">
        <form method="get" className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div>
            <label className="block text-sm text-gray-600 mb-2">笔记日期</label>
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
          <div>
            <label className="block text-sm text-gray-600 mb-2">分类</label>
            <select
              name="categoryId"
              defaultValue={categoryId || ''}
              className="input"
            >
              <option value="">全部分类</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-2">每页数量</label>
            <select
              name="pageSize"
              defaultValue={pageSize}
              className="input"
            >
              {PAGE_SIZE_OPTIONS.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-3">
            <input type="hidden" name="page" value="1" />
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
          {categoryId ? `，分类ID：${categoryId}` : ''}
        </div>
      </div>

      {/* 笔记列表 + 批量操作 */}
      {posts.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500 mb-4">未找到笔记</p>
          <Link href="/posts/new" className="btn btn-primary">
            写一篇
          </Link>
        </div>
      ) : (
        <PostListWithActions posts={posts as any} />
      )}

      {/* 分页 */}
      <div className="mt-6 flex items-center justify-between text-sm text-gray-600">
        <div>
          共 {total} 条记录，当前第 {page} / {totalPages} 页，每页 {pageSize} 条
        </div>
        <div className="flex items-center gap-2">
          {page > 1 && (
            <Link href={buildPageHref(page - 1)} className="btn btn-secondary text-sm px-3 py-1">
              上一页
            </Link>
          )}
          {page < totalPages && (
            <Link href={buildPageHref(page + 1)} className="btn btn-secondary text-sm px-3 py-1">
              下一页
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

