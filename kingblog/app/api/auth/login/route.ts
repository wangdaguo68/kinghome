import { NextRequest, NextResponse } from 'next/server';
import { verifyLogin, setLoginSession } from '@/lib/auth';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;
    
    if (!username || !password) {
      return NextResponse.json(
        { success: false, error: '用户名和密码不能为空' },
        { status: 400 }
      );
    }
    
    const user = await verifyLogin(username, password);
    
    if (!user) {
      // 检查用户是否存在
      const { query } = await import('@/lib/db');
      const checkUser = await query('SELECT username FROM users WHERE username = ?', [username]) as any[];
      
      if (checkUser.length === 0) {
        return NextResponse.json(
          { success: false, error: '用户不存在，请先初始化用户（访问 /api/auth/init）' },
          { status: 401 }
        );
      }
      
      return NextResponse.json(
        { success: false, error: '密码错误' },
        { status: 401 }
      );
    }
    
    await setLoginSession(user.id);
    
    return NextResponse.json({
      success: true,
      data: {
        id: user.id,
        username: user.username,
        nickname: user.nickname,
      },
    });
  } catch (error: any) {
    console.error('Login API error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

