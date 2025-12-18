'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';
import RichTextEditor from '@/components/RichTextEditor';

interface Category {
  id: number;
  name: string;
  description: string | null;
}

const DEFAULT_CATEGORIES = ['日复盘', '周复盘', '月复盘', '年度总结', '随笔'];

export default function NewPost() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [loadingYesterday, setLoadingYesterday] = useState(true);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [showNewCategory, setShowNewCategory] = useState(false);
  const [formData, setFormData] = useState({
    title: format(new Date(), 'yyyyMMdd'),
    content: '',
    summary: '',
    plan: '',
    mood: '开心',
    date: format(new Date(), 'yyyy-MM-dd'),
    status: 'published' as 'draft' | 'published',
  });

  // 加载分类列表，若缺少默认分类则自动创建并选中“日复盘”
  useEffect(() => {
    const ensureCategories = async () => {
      try {
        const response = await fetch('/api/categories');
        const result = await response.json();

        let list: Category[] = result.success ? result.data : [];

        const existingNames = new Set(list.map((c: Category) => c.name));
        const missing = DEFAULT_CATEGORIES.filter((n) => !existingNames.has(n));

        if (missing.length > 0) {
          for (const name of missing) {
            await fetch('/api/categories', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name }),
            });
          }
          // 重新拉取
          const refetch = await fetch('/api/categories');
          const refetchResult = await refetch.json();
          if (refetchResult.success) {
            list = refetchResult.data;
          }
        }

        setCategories(list);

        // 默认选中“日复盘”
        const daily = list.find((c: Category) => c.name === '日复盘');
        if (daily) {
          setSelectedCategories([daily.id]);
        }
      } catch (error) {
        console.error('Load categories error:', error);
      }
    };
    ensureCategories();
  }, []);

  // 加载最近一篇"日复盘"类型的复盘
  useEffect(() => {
    const loadLatestDailyPost = async () => {
      try {
        const response = await fetch('/api/posts/yesterday');
        const result = await response.json();
        if (result.success && result.data) {
          const latestDaily = result.data;
          // 将最近一篇日复盘的内容填充到表单中（作为参考）
          setFormData((prev) => ({
            ...prev,
            summary: latestDaily.summary || '',
            content: latestDaily.content || '',
            plan: latestDaily.plan || '',
          }));
        }
      } catch (error) {
        console.error('Load latest daily post error:', error);
      } finally {
        setLoadingYesterday(false);
      }
    };
    loadLatestDailyPost();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const isDailySelected = selectedCategories.some(
      (id) => categories.find((c) => c.id === id)?.name === '日复盘'
    );

    try {
      const response = await fetch('/api/posts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          summary: isDailySelected ? formData.summary : '',
          plan: isDailySelected ? formData.plan : '',
          categoryIds: selectedCategories,
        }),
      });

      const result = await response.json();

      if (result.success) {
        router.push(`/posts/${result.data.id}`);
      } else {
        alert('创建失败: ' + result.error);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('创建失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) {
      alert('请输入分类名称');
      return;
    }

    try {
      const response = await fetch('/api/categories', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: newCategoryName.trim() }),
      });

      const result = await response.json();

      if (result.success) {
        // 重新加载分类列表
        const categoriesResponse = await fetch('/api/categories');
        const categoriesResult = await categoriesResponse.json();
        if (categoriesResult.success) {
          setCategories(categoriesResult.data);
          // 选中新创建的分类
          const newCategory = categoriesResult.data.find(
            (c: Category) => c.id === result.data.id
          );
          if (newCategory) {
            setSelectedCategories([...selectedCategories, newCategory.id]);
          }
        }
        setNewCategoryName('');
        setShowNewCategory(false);
      } else {
        alert('创建分类失败: ' + result.error);
      }
    } catch (error) {
      console.error('Create category error:', error);
      alert('创建分类失败，请重试');
    }
  };

  const toggleCategory = (categoryId: number) => {
    setSelectedCategories((prev) => {
      let next: number[];
      if (prev.includes(categoryId)) {
        next = prev.filter((id) => id !== categoryId);
      } else {
        next = [...prev, categoryId];
      }

      // 如果取消了“日复盘”，清空今日总结和明日计划
      const hasDaily = next.some(
        (id) => categories.find((c) => c.id === id)?.name === '日复盘'
      );
      if (!hasDaily) {
        setFormData((old) => ({
          ...old,
          summary: '',
          plan: '',
        }));
      }

      return next;
    });
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">写笔记</h1>

      {loadingYesterday && (
        <div className="card mb-6 text-center py-4 text-gray-500">
          正在加载最近一篇日复盘内容...
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-6">
        {/* 标题 */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
            标题 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="title"
            name="title"
            required
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="input"
            placeholder="例如：2025年12月15日复盘"
          />
        </div>

        {/* 日期、心情和分类 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-2">
              笔记日期 <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              id="date"
              name="date"
              required
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label htmlFor="mood" className="block text-sm font-medium text-gray-700 mb-2">
              心情/状态
            </label>
            <input
              type="text"
              id="mood"
              name="mood"
              value={formData.mood}
              onChange={(e) => setFormData({ ...formData, mood: e.target.value })}
              className="input"
              placeholder="例如：充实、疲惫、开心"
            />
          </div>
        </div>

        {/* 分类选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            分类
          </label>
          <div className="flex flex-wrap gap-2 mb-2">
            {categories.map((category) => (
              <button
                key={category.id}
                type="button"
                onClick={() => toggleCategory(category.id)}
                className={`px-3 py-1 rounded-full text-sm transition-colors ${
                  selectedCategories.includes(category.id)
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {category.name}
              </button>
            ))}
            {!showNewCategory && (
              <button
                type="button"
                onClick={() => setShowNewCategory(true)}
                className="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-600 hover:bg-gray-200 border border-dashed border-gray-300"
              >
                + 新建分类
              </button>
            )}
          </div>
          {showNewCategory && (
            <div className="flex gap-2">
              <input
                type="text"
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                className="input flex-1"
                placeholder="输入新分类名称"
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleCreateCategory();
                  }
                }}
              />
              <button
                type="button"
                onClick={handleCreateCategory}
                className="btn btn-primary"
              >
                创建
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowNewCategory(false);
                  setNewCategoryName('');
                }}
                className="btn btn-secondary"
              >
                取消
              </button>
            </div>
          )}
        </div>

        {/* 笔记内容 - 富文本编辑器 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            笔记内容 <span className="text-red-500">*</span>
          </label>
          <RichTextEditor
            value={formData.content}
            onChange={(value) => setFormData({ ...formData, content: value })}
            placeholder="详细记录今天的思考、遇到的问题、解决方案等..."
          />
        </div>

        {/* 今日总结 - 富文本编辑器（仅日复盘显示） */}
        {selectedCategories.some(
          (id) => categories.find((c) => c.id === id)?.name === '日复盘'
        ) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              今日总结
            </label>
            <RichTextEditor
              value={formData.summary}
              onChange={(value) => setFormData({ ...formData, summary: value })}
              placeholder="简要总结今天的主要收获和感受..."
            />
          </div>
        )}

        {/* 明日计划 - 富文本编辑器（仅日复盘显示） */}
        {selectedCategories.some(
          (id) => categories.find((c) => c.id === id)?.name === '日复盘'
        ) && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              明日计划
            </label>
            <RichTextEditor
              value={formData.plan}
              onChange={(value) => setFormData({ ...formData, plan: value })}
              placeholder="列出明天要完成的主要任务..."
            />
          </div>
        )}

        {/* 状态 */}
        <div>
          <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
            状态
          </label>
          <select
            id="status"
            name="status"
            value={formData.status}
            onChange={(e) =>
              setFormData({
                ...formData,
                status: e.target.value as 'draft' | 'published',
              })
            }
            className="input"
          >
            <option value="published">发布</option>
            <option value="draft">草稿</option>
          </select>
        </div>

        {/* 提交按钮 */}
        <div className="flex gap-4 pt-4">
          <button
            type="submit"
            disabled={loading || !formData.content.trim()}
            className="btn btn-primary flex-1"
          >
            {loading ? '保存中...' : '保存笔记'}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="btn btn-secondary"
          >
            取消
          </button>
        </div>
      </form>
    </div>
  );
}
