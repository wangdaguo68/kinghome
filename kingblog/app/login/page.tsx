'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [initLoading, setInitLoading] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  // 检查是否已登录
  useEffect(() => {
    const checkLogin = async () => {
      try {
        const response = await fetch('/api/auth/me');
        const result = await response.json();
        if (result.success) {
          router.push('/');
        }
      } catch (error) {
        // 未登录，继续显示登录页
      }
    };
    checkLogin();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const result = await response.json();

      if (result.success) {
        // 登录成功，跳转到首页
        router.push('/');
        router.refresh();
      } else {
        // 如果提示需要初始化用户
        if (result.error.includes('初始化')) {
          const shouldInit = confirm('用户不存在，是否现在初始化用户？\n（将创建用户名：admin，密码：admin）');
          if (shouldInit) {
            handleInitUser();
            return;
          }
        }
        alert('登录失败: ' + result.error);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleInitUser = async () => {
    setInitLoading(true);
    try {
      const response = await fetch('/api/auth/init', {
        method: 'POST',
      });
      const result = await response.json();
      
      if (result.success) {
        alert(result.message + '\n\n现在可以使用 admin/admin 登录了');
        setFormData({ username: 'admin', password: 'admin' });
      } else {
        alert('初始化失败: ' + result.error);
      }
    } catch (error) {
      console.error('Error:', error);
      alert('初始化失败，请重试');
    } finally {
      setInitLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            KingBlog 登录
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            记录每一天的思考与成长
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="card space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                用户名
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                value={formData.username}
                onChange={handleChange}
                className="input"
                placeholder="请输入用户名"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                密码
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                className="input"
                placeholder="请输入密码"
              />
            </div>
          </div>

          <div className="space-y-3">
            <button
              type="submit"
              disabled={loading || initLoading}
              className="btn btn-primary w-full"
            >
              {loading ? '登录中...' : '登录'}
            </button>
            <button
              type="button"
              onClick={handleInitUser}
              disabled={loading || initLoading}
              className="btn btn-secondary w-full text-sm"
            >
              {initLoading ? '初始化中...' : '初始化用户（admin/admin）'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

