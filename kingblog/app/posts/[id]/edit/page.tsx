'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { format } from 'date-fns';
import RichTextEditor from '@/components/RichTextEditor';

interface Category {
  id: number;
  name: string;
  description: string | null;
}

export default function EditPost() {
  const router = useRouter();
  const params = useParams();
  const postId = params.id as string;
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [showNewCategory, setShowNewCategory] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    summary: '',
    plan: '',
    mood: '',
    date: format(new Date(), 'yyyy-MM-dd'),
    status: 'published' as 'draft' | 'published',
  });

  // 加载分类列表
  useEffect(() => {
    const loadCategories = async () => {
      try {
        const response = await fetch('/api/categories');
        const result = await response.json();
        if (result.success) {
          setCategories(result.data);
        }
      } catch (error) {
        console.error('Load categories error:', error);
      }
    };
    loadCategories();
  }, []);

  // 加载复盘数据
  useEffect(() => {
    const loadPost = async () => {
      try {
        const response = await fetch(`/api/posts/${postId}`);
        const result = await response.json();

        if (result.success) {
          const post = result.data;
          setFormData({
            title: post.title,
            content: post.content,
            summary: post.summary || '',
            plan: post.plan || '',
            mood: post.mood || '',
            date: post.date,
            status: post.status,
          });

          // 加载分类
          if (post.categories) {
            setSelectedCategories(post.categories.map((c: Category) => c.id));
          }
        } else {
          alert('加载失败: ' + result.error);
          router.push('/');
        }
      } catch (error) {
        console.error('Error:', error);
        alert('加载失败，请重试');
        router.push('/');
      } finally {
        setLoading(false);
      }
    };

    if (postId) {
      loadPost();
    }
  }, [postId, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const response = await fetch(`/api/posts/${postId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          categoryIds: selectedCategories,
        }),
      });

      const result = await response.json();

      if (result.success) {
        router.push(`/posts/${postId}`);
      } else {
        alert('更新失败: ' + result.error);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('更新失败，请重试');
    } finally {
      setSaving(false);
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
        const categoriesResponse = await fetch('/api/categories');
        const categoriesResult = await categoriesResponse.json();
        if (categoriesResult.success) {
          setCategories(categoriesResult.data);
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
    if (selectedCategories.includes(categoryId)) {
      setSelectedCategories(selectedCategories.filter((id) => id !== categoryId));
    } else {
      setSelectedCategories([...selectedCategories, categoryId]);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <p className="text-gray-500">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">编辑复盘</h1>

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
            placeholder="例如：2024年1月1日复盘"
          />
        </div>

        {/* 日期和心情 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-2">
              复盘日期 <span className="text-red-500">*</span>
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

        {/* 复盘内容 - 富文本编辑器 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            复盘内容 <span className="text-red-500">*</span>
          </label>
          <RichTextEditor
            value={formData.content}
            onChange={(value) => setFormData({ ...formData, content: value })}
            placeholder="详细记录今天的思考、遇到的问题、解决方案等..."
          />
        </div>

        {/* 今日总结 - 富文本编辑器 */}
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

        {/* 明日计划 - 富文本编辑器 */}
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
            disabled={saving || !formData.content.trim()}
            className="btn btn-primary flex-1"
          >
            {saving ? '保存中...' : '保存修改'}
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
