import { NextResponse } from 'next/server';
import { query } from '@/lib/db';

// 初始化admin用户（仅用于开发环境）
export async function POST() {
  try {
    // 检查是否已存在admin用户
    const checkSql = 'SELECT id FROM users WHERE username = ?';
    const existing = await query(checkSql, ['admin']) as any[];
    
    if (existing.length > 0) {
      // 更新密码为admin
      const updateSql = 'UPDATE users SET password = ? WHERE username = ?';
      await query(updateSql, ['admin', 'admin']);
      return NextResponse.json({
        success: true,
        message: '用户已存在，密码已重置为 admin',
      });
    }
    
    // 创建新用户
    const insertSql = `
      INSERT INTO users (username, password, nickname, email)
      VALUES (?, ?, ?, ?)
    `;
    await query(insertSql, ['admin', 'admin', '管理员', 'admin@example.com']);
    
    return NextResponse.json({
      success: true,
      message: '用户创建成功：用户名 admin，密码 admin',
    });
  } catch (error: any) {
    console.error('Init user error:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// GET - 检查用户是否存在
export async function GET() {
  try {
    const sql = 'SELECT id, username, nickname FROM users WHERE username = ?';
    const results = await query(sql, ['admin']) as any[];
    
    return NextResponse.json({
      success: true,
      exists: results.length > 0,
      user: results.length > 0 ? results[0] : null,
    });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

