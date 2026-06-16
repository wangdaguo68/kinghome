import 'package:flutter/material.dart';

import '../main.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/shell.dart';
import 'card_screen.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        if (state.records.isEmpty) {
          return const Center(
            child: Text('还没有记录。先从首页开始留下一条。', style: TextStyle(color: muted)),
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 26),
          itemBuilder: (context, index) =>
              _RecordTile(record: state.records[index]),
          separatorBuilder: (_, _) => const SizedBox(height: 12),
          itemCount: state.records.length,
        );
      },
    );
  }
}

class _RecordTile extends StatelessWidget {
  const _RecordTile({required this.record});

  final EmotionRecord record;

  @override
  Widget build(BuildContext context) {
    final summary = record.summary;
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => RecordDetailScreen(recordId: record.id),
        ),
      ),
      child: SoftPanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  _date(record.createdAt),
                  style: const TextStyle(color: muted),
                ),
                Text(record.moodEmoji, style: const TextStyle(fontSize: 24)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              summary == null ? record.moodLabel : summary.keywords.join('、'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 6),
            Text(
              summary?.comfortSentence ?? '这一段还在慢慢沉淀。',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  String _date(DateTime date) => '${date.month}月${date.day}日';
}

class RecordDetailScreen extends StatelessWidget {
  const RecordDetailScreen({super.key, required this.recordId});

  final String recordId;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        final record = state.recordById(recordId);
        if (record == null) {
          return const WarmScaffold(child: Center(child: Text('记录已删除')));
        }
        return WarmScaffold(
          appBar: AppBar(
            title: Text('${record.moodEmoji} ${record.moodLabel}'),
            actions: [
              IconButton(
                tooltip: '删除',
                onPressed: () async {
                  await state.deleteRecord(record.id);
                  if (context.mounted) {
                    Navigator.of(context).pop();
                  }
                },
                icon: const Icon(Icons.delete_outline),
              ),
            ],
          ),
          child: ListView(
            padding: const EdgeInsets.all(18),
            children: [
              if (record.summary != null)
                SoftPanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        record.summary!.keywords.join('、'),
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        record.summary!.summary,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton.icon(
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => CardScreen(recordId: record.id),
                          ),
                        ),
                        icon: const Icon(Icons.image_outlined),
                        label: const Text('查看治愈卡片'),
                      ),
                    ],
                  ),
                ),
              const SizedBox(height: 14),
              ...record.messages.map((message) {
                final isUser = message.role == ChatRole.user;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Align(
                    alignment: isUser
                        ? Alignment.centerRight
                        : Alignment.centerLeft,
                    child: Container(
                      constraints: BoxConstraints(
                        maxWidth: MediaQuery.of(context).size.width * 0.78,
                      ),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 15,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: isUser
                            ? clay.withValues(alpha: 0.34)
                            : Colors.white.withValues(alpha: 0.72),
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Text(
                        message.content,
                        style: const TextStyle(height: 1.55, color: ink),
                      ),
                    ),
                  ),
                );
              }),
            ],
          ),
        );
      },
    );
  }
}
