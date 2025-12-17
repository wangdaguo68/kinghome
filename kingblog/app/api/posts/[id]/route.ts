import { NextRequest, NextResponse } from 'next/server';
import { getPostById, updatePost, deletePost, incrementViews } from '@/lib/posts';
import { getPostCategories } from '@/lib/categories';
import { getCurrentUser } from '@/lib/auth';

// GET - 获取单个复盘
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const id = parseInt(params.id);
    const post = await getPostById(id);
    
    if (!post) {
      return NextResponse.json(
        { success: false, error: '复盘不存在' },
        { status: 404 }
      );
    }
    
    // 获取分类
    const categories = await getPostCategories(id);
    
    // 增加浏览次数
    await incrementViews(id);
    post.views += 1;
    
    return NextResponse.json({ 
      success: true, 
      data: { ...post, categories } 
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// PUT - 更新复盘
export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    // 检查登录状态
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json(
        { success: false, error: '请先登录' },
        { status: 401 }
      );
    }

    const id = parseInt(params.id);
    const body = await request.json();
    const { categoryIds, ...postData } = body;
    
    const success = await updatePost(id, postData);
    
    if (!success) {
      return NextResponse.json(
        { success: false, error: '没有要更新的字段' },
        { status: 400 }
      );
    }
    
    // 更新分类关联
    if (categoryIds !== undefined) {
      const { setPostCategories } = await import('@/lib/categories');
      await setPostCategories(id, categoryIds || []);
    }
    
    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// DELETE - 删除复盘
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const id = parseInt(params.id);
    await deletePost(id);
    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

