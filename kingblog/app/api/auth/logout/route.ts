import { NextResponse } from 'next/server';
import { clearLoginSession } from '@/lib/auth';

export async function POST() {
  try {
    await clearLoginSession();
    return NextResponse.json({ success: true });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

