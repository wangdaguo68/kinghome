import { cookies } from 'next/headers';
import { query } from './db';
import bcrypt from 'bcryptjs';

export interface User {
  id: number;
  username: string;
  nickname: string | null;
  email: string | null;
}

// 验证用户登录
export async function verifyLogin(username: string, password: string): Promise<User | null> {
  try {
    const sql = 'SELECT * FROM users WHERE username = ?';
    const results = await query(sql, [username]) as any[];
    
    if (results.length === 0) {
      return null;
    }
    
    const user = results[0];
    
    // 验证密码（支持bcrypt和明文密码，方便初始使用）
    let isValid = false;
    if (user.password.startsWith('$2')) {
      // bcrypt加密的密码
      isValid = await bcrypt.compare(password, user.password);
    } else {
      // 明文密码（仅用于开发环境）
      isValid = user.password === password;
    }
    
    if (!isValid) {
      return null;
    }
    
    return {
      id: user.id,
      username: user.username,
      nickname: user.nickname,
      email: user.email,
    };
  } catch (error) {
    console.error('Login error:', error);
    return null;
  }
}

// 获取当前登录用户
export async function getCurrentUser(): Promise<User | null> {
  try {
    const cookieStore = await cookies();
    const userId = cookieStore.get('user_id')?.value;
    
    if (!userId) {
      return null;
    }
    
    const sql = 'SELECT id, username, nickname, email FROM users WHERE id = ?';
    const results = await query(sql, [userId]) as any[];
    
    if (results.length === 0) {
      return null;
    }
    
    return results[0] as User;
  } catch (error) {
    console.error('Get user error:', error);
    return null;
  }
}

// 设置登录session
export async function setLoginSession(userId: number) {
  const cookieStore = await cookies();
  cookieStore.set('user_id', userId.toString(), {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 30, // 30天
  });
}

// 清除登录session
export async function clearLoginSession() {
  const cookieStore = await cookies();
  cookieStore.delete('user_id');
}

