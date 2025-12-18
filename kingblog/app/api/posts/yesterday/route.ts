import { NextResponse } from 'next/server';
import { getLatestDailyPost } from '@/lib/posts';
import { getCurrentUser } from '@/lib/auth';

// 标记为动态路由，避免构建时静态预渲染使用 cookies 报错
export const dynamic = 'force-dynamic';

// GET - 获取最近一篇"日复盘"类型的复盘
export async function GET() {
  try {
    const user = await getCurrentUser();
    if (!user) {
      return NextResponse.json(
        { success: false, error: '请先登录' },
        { status: 401 }
      );
    }

    const latestDailyPost = await getLatestDailyPost(user.id);
    return NextResponse.json({ success: true, data: latestDailyPost });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

