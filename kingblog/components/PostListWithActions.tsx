'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface Post {
  id: number;
  title: string;
  date: string;
  mood?: string | null;
  status: 'draft' | 'published';
  summary?: string | null;
  views: number;
}

interface PostListWithActionsProps {
  posts: Post[];
}

export default function PostListWithActions({ posts }: PostListWithActionsProps) {
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    if (selectedIds.length === posts.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(posts.map((p) => p.id));
    }
  };

  const handleDelete = async (ids: number[]) => {
    if (!ids.length) return;
    if (!confirm(`确定要删除选中的 ${ids.length} 条笔记吗？此操作不可恢复。`)) {
      return;
    }
    try {
      const res = await fetch('/api/posts/batch-delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      });
      const data = await res.json();
      if (!data.success) {
        alert('删除失败：' + data.error);
        return;
      }
      setSelectedIds([]);
      router.refresh();
    } catch (e) {
      console.error(e);
      alert('删除失败，请稍后重试');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={selectedIds.length === posts.length && posts.length > 0}
              onChange={toggleSelectAll}
            />
            <span>全选本页</span>
          </label>
          <span>已选中 {selectedIds.length} 条</span>
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          disabled={selectedIds.length === 0}
          onClick={() => handleDelete(selectedIds)}
        >
          删除选中
        </button>
      </div>

      <div className="space-y-6">
        {posts.map((post) => (
          <article
            key={post.id}
            className="card hover:shadow-md transition-shadow duration-200"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4"
                  checked={selectedIds.includes(post.id)}
                  onChange={() => toggleSelect(post.id)}
                />
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
              <button
                type="button"
                className="text-sm text-red-500 hover:text-red-600"
                onClick={() => handleDelete([post.id])}
              >
                删除
              </button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}


