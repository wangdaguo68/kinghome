import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// 需要登录的页面路径
const protectedPaths = ['/posts/new', '/posts', '/api/posts'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // API路由保护
  if (pathname.startsWith('/api/posts') && pathname !== '/api/posts') {
    const userId = request.cookies.get('user_id');
    if (!userId) {
      return NextResponse.json(
        { success: false, error: '请先登录' },
        { status: 401 }
      );
    }
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/posts/:path*', '/api/posts/:path*'],
};

