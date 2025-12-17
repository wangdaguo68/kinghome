import { notFound } from 'next/navigation';
import Link from 'next/link';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { getPostById } from '@/lib/posts';
import { getPostCategories } from '@/lib/categories';

export default async function PostDetail({
  params,
}: {
  params: { id: string };
}) {
  const post = await getPostById(parseInt(params.id));
  
  if (!post) {
    notFound();
  }
  
  // 获取分类
  const categories = await getPostCategories(post.id);

  return (
    <article className="max-w-4xl mx-auto">
      {/* 返回按钮 */}
      <Link
        href="/"
        className="inline-flex items-center text-gray-600 hover:text-primary-600 mb-6 transition-colors"
      >
        ← 返回首页
      </Link>

      {/* 文章内容 */}
      <div className="card">
        {/* 标题和元信息 */}
        <header className="mb-8 pb-6 border-b border-gray-200">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            {post.title}
          </h1>
          <div className="flex items-center flex-wrap gap-4 text-sm text-gray-500">
            <time>
              {format(new Date(post.date), 'yyyy年MM月dd日 EEEE', {
                locale: zhCN,
              })}
            </time>
            {post.mood && (
              <span className="px-3 py-1 bg-primary-100 text-primary-700 rounded-full">
                {post.mood}
              </span>
            )}
            {categories && categories.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {categories.map((category) => (
                  <span
                    key={category.id}
                    className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full"
                  >
                    {category.name}
                  </span>
                ))}
              </div>
            )}
            <span>{post.views} 次浏览</span>
          </div>
        </header>

        {/* 今日总结 */}
        {post.summary && (
          <section className="mb-8 p-4 bg-blue-50 rounded-lg border-l-4 border-blue-500">
            <h2 className="font-semibold text-blue-900 mb-2">今日总结</h2>
            <div
              className="text-blue-800 prose prose-blue max-w-none"
              dangerouslySetInnerHTML={{ __html: post.summary }}
            />
          </section>
        )}

        {/* 复盘内容 */}
        <section className="mb-8">
          <div
            className="prose max-w-none text-gray-700"
            dangerouslySetInnerHTML={{ __html: post.content }}
          />
        </section>

        {/* 明日计划 */}
        {post.plan && (
          <section className="p-4 bg-green-50 rounded-lg border-l-4 border-green-500">
            <h2 className="font-semibold text-green-900 mb-2">明日计划</h2>
            <div
              className="text-green-800 prose prose-green max-w-none"
              dangerouslySetInnerHTML={{ __html: post.plan }}
            />
          </section>
        )}

        {/* 操作按钮 */}
        <div className="mt-8 pt-6 border-t border-gray-200 flex gap-4">
          <Link
            href={`/posts/${post.id}/edit`}
            className="btn btn-secondary"
          >
            编辑
          </Link>
        </div>
      </div>
    </article>
  );
}
