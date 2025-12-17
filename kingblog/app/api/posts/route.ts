import { NextRequest, NextResponse } from 'next/server';
import { getPosts, createPost } from '@/lib/posts';
import { getCurrentUser } from '@/lib/auth';
import { setPostCategories } from '@/lib/categories';

// GET - 获取所有复盘（支持状态/日期过滤）
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const statusParam = searchParams.get('status') as 'draft' | 'published' | 'all' | null;
    const dateParam = searchParams.get('date');

    const posts = await getPosts({
      status: statusParam || 'published',
      date: dateParam || undefined,
    });

    return NextResponse.json({ success: true, data: posts });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// POST - 创建新复盘
export async function POST(request: NextRequest) {
  try {
    // 检查登录状态
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json(
        { success: false, error: '请先登录' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const { title, content, summary, plan, mood, date, status, categoryIds } = body;
    
    // 验证必填字段
    if (!title || !content || !date) {
      return NextResponse.json(
        { success: false, error: '标题、内容和日期为必填项' },
        { status: 400 }
      );
    }
    
    // 创建复盘
    const postId = await createPost({
      user_id: user.id,
      title,
      content,
      summary: summary || null,
      plan: plan || null,
      mood: mood || null,
      date,
      status: status || 'published',
    });
    
    // 设置分类关联
    if (categoryIds && categoryIds.length > 0) {
      await setPostCategories(postId, categoryIds);
    }
    
    return NextResponse.json({ success: true, data: { id: postId } });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

