import { NextRequest, NextResponse } from 'next/server';
import { deletePosts } from '@/lib/posts';
import { getCurrentUser } from '@/lib/auth';

// 批量删除复盘
export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json(
        { success: false, error: '请先登录' },
        { status: 401 }
      );
    }

    const body = await request.json();
    const ids = (body.ids || []) as number[];

    if (!Array.isArray(ids) || ids.length === 0) {
      return NextResponse.json(
        { success: false, error: '请选择要删除的笔记' },
        { status: 400 }
      );
    }

    await deletePosts(ids.map((id) => Number(id)));

    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}


