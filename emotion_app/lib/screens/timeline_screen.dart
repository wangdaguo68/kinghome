import 'package:flutter/material.dart';

import '../main.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/shell.dart';
import 'history_screen.dart';

class TimelineScreen extends StatelessWidget {
  const TimelineScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        final records = [...state.records]
          ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
        return ListView(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 26),
          children: [
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '时间轴',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '不是聊天记录，是你慢慢走过来的证据。',
                    style: TextStyle(color: muted, height: 1.55),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            if (records.isEmpty)
              const SoftPanel(
                child: Text(
                  '还没有时间轴。先在首页留下第一条记录。',
                  style: TextStyle(color: muted, height: 1.55),
                ),
              )
            else ...[
              SoftPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('最近的情绪线索', style: TextStyle(color: muted)),
                    const SizedBox(height: 8),
                    Text(
                      state.emotionInsightText,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              SoftPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('我撑过去的事', style: TextStyle(color: muted)),
                    const SizedBox(height: 8),
                    Text(
                      state.survivedMomentText,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              ...records.map(
                (record) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _TimelineCard(record: record),
                ),
              ),
            ],
            const SizedBox(height: 6),
            OutlinedButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const HistoryScreen()),
                );
              },
              icon: const Icon(Icons.list_alt_outlined),
              label: const Text('查看完整记录'),
            ),
          ],
        );
      },
    );
  }
}

class _TimelineCard extends StatelessWidget {
  const _TimelineCard({required this.record});

  final EmotionRecord record;

  @override
  Widget build(BuildContext context) {
    final summary = record.summary;
    final latest = record.messages.isEmpty ? null : record.messages.last;
    return SoftPanel(
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
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: wheat.withValues(alpha: 0.22),
              borderRadius: BorderRadius.circular(999),
            ),
            child: const Text(
              '这一天也算数',
              style: TextStyle(
                color: deepBlue,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const SizedBox(height: 10),
          Text(
            summary?.summary ??
                '${record.moodLabel}，${latest?.content ?? '还没有展开。'}',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            summary?.comfortSentence ?? '这一段还在写，继续说下去，它会变得更清楚。',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (summary != null) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: summary.keywords
                  .map(
                    (keyword) =>
                        Chip(label: Text(keyword), backgroundColor: mist),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }

  String _date(DateTime date) =>
      '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';
}
