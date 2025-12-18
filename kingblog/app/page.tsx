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
  const categoryIdRaw = searchParams?.categoryId;
  const pageParam = Number(searchParams?.page) || 1;
  const sizeParam = Number(searchParams?.pageSize) || 10;
  const pageSize = PAGE_SIZE_OPTIONS.includes(sizeParam) ? sizeParam : 10;
  const page = pageParam > 0 ? pageParam : 1;

  // 先获取所有分类，用于确定默认的“日复盘”分类
  const categories = await getAllCategories();
  const defaultDailyCategory = categories.find((c) => c.name === '日复盘');

  // 计算实际生效的分类筛选：
  // - 未传 categoryId 参数：默认使用“日复盘”
  // - 传了空字符串 ""：表示全部分类，不做分类过滤
  // - 传了具体 id：按该分类过滤
  let effectiveCategoryId: number | undefined;
  if (categoryIdRaw === undefined) {
    effectiveCategoryId = defaultDailyCategory?.id;
  } else if (categoryIdRaw === '') {
    effectiveCategoryId = undefined;
  } else {
    effectiveCategoryId = Number(categoryIdRaw);
  }

  const [posts, total] = await Promise.all([
    getPosts({
      status,
      date: date || undefined,
      categoryId: effectiveCategoryId,
      page,
      pageSize,
    }),
    countPosts({
      status,
      date: date || undefined,
      categoryId: effectiveCategoryId,
    }),
  ]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const buildPageHref = (targetPage: number) => {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    if (status) params.set('status', status);
    if (categoryIdRaw !== undefined) {
      // 用户有显式选择分类（包括空字符串表示全部分类）
      params.set('categoryId', categoryIdRaw);
    } else if (effectiveCategoryId) {
      // 初始默认“日复盘”时，把分类写入 URL，避免分页链接丢失
      params.set('categoryId', String(effectiveCategoryId));
    }
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
              defaultValue={categoryIdRaw ?? (defaultDailyCategory?.id ?? '')}
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
          {categoryIdRaw === ''
            ? '，分类：全部分类'
            : effectiveCategoryId
            ? `，分类ID：${effectiveCategoryId}`
            : ''}
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

