import 'package:flutter/material.dart';

import '../main.dart';
import '../theme.dart';
import '../widgets/shell.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        return ListView(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 26),
          children: [
            SoftPanel(
              child: Row(
                children: [
                  Container(
                    width: 58,
                    height: 58,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: clay.withValues(alpha: 0.34),
                    ),
                    child: const Center(
                      child: Text(
                        '不',
                        style: TextStyle(
                          fontSize: 26,
                          color: ink,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '不想说',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        Text(
                          '今日剩余 ${state.freeCountToday} 次 AI 回复',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        if (state.recoveryCode != null)
                          Text(
                            '恢复码：${state.recoveryCode}',
                            style: const TextStyle(
                              color: muted,
                              fontSize: 12,
                              height: 1.4,
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _MenuItem(
              icon: Icons.event_available_outlined,
              title: '每日打卡',
              subtitle: '查看连续天数和最近打卡',
              onTap: () => _showInfo(
                context,
                title: '每日打卡',
                message: '打卡会保存在本机，用来记录每天的小坐标。入口在底部导航的「打卡」。',
              ),
            ),
            _MenuItem(
              icon: Icons.mark_unread_chat_alt_outlined,
              title: '同频纸条',
              subtitle: '匿名投出和接住纸条',
              onTap: () => _showInfo(
                context,
                title: '同频纸条',
                message: '同频纸条是真实匿名投递，但不开放陌生人聊天，只能用预设按钮回应。入口在底部导航的「纸条」。',
              ),
            ),
            _MenuItem(
              icon: Icons.query_stats_outlined,
              title: '本周周报',
              subtitle: '查看这一周的情绪变化',
              onTap: () => _showInfo(
                context,
                title: '本周周报',
                message: '你可以从首页直接打开周报。它会根据最近 7 天的记录自动整理。',
              ),
            ),
            _MenuItem(
              icon: Icons.mail_outline,
              title: '未来信箱',
              subtitle: '把今天的话留给未来',
              onTap: () => _showInfo(
                context,
                title: '未来信箱',
                message: '未来信箱会把你写下的内容保存在本机，到时间后自动打开。',
              ),
            ),
            _MenuItem(
              icon: Icons.lock_outline,
              title: '匿名身份',
              subtitle: '已启用服务端每日额度',
              onTap: () => _showInfo(
                context,
                title: '匿名身份',
                message:
                    '当前版本会为本机生成匿名身份，并把每日 AI 回复额度放到服务器判断。恢复码请先自己保存，后续会补恢复入口。',
              ),
            ),
            _MenuItem(
              icon: Icons.file_download_outlined,
              title: '数据导出',
              subtitle: '后续支持 JSON 导出',
              onTap: () => _showInfo(
                context,
                title: '数据导出',
                message: '当前版本还没有导出入口，但底层数据已经结构化了，后面可以直接补。',
              ),
            ),
            _MenuItem(
              icon: Icons.delete_outline,
              title: '清空记录',
              subtitle: '删除本机保存的全部情绪记录',
              destructive: true,
              onTap: () => _confirmClear(context),
            ),
            _MenuItem(
              icon: Icons.info_outline,
              title: '关于 App',
              subtitle: '情绪沉淀工具，不做医疗诊断',
              onTap: () => _showInfo(
                context,
                title: '关于不想说',
                message: '不想说是一款情绪沉淀 App，重点是时间轴、未来信箱和周报，不提供医疗诊断或心理咨询服务。',
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showInfo(
    BuildContext context, {
    required String title,
    required String message,
  }) {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmClear(BuildContext context) {
    final state = AppScope.of(context);
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('清空记录'),
        content: const Text('这会删除本机保存的全部情绪记录，删除后不能恢复。'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () async {
              await state.clearRecords();
              if (context.mounted) {
                Navigator.of(context).pop();
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(const SnackBar(content: Text('记录已清空')));
              }
            },
            child: const Text('清空'),
          ),
        ],
      ),
    );
  }
}

class _MenuItem extends StatelessWidget {
  const _MenuItem({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.destructive = false,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  final bool destructive;

  @override
  Widget build(BuildContext context) {
    final accent = destructive ? const Color(0xFF9B4E43) : deepBlue;
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: SoftPanel(
          child: Row(
            children: [
              Icon(icon, color: accent),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        color: destructive ? accent : ink,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: const TextStyle(color: muted, height: 1.45),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: destructive ? accent : muted),
            ],
          ),
        ),
      ),
    );
  }
}
