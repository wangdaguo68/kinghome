import 'package:flutter/material.dart';

import '../main.dart';
import '../theme.dart';
import '../widgets/shell.dart';

class ReportScreen extends StatelessWidget {
  const ReportScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        final report = state.buildWeeklyReport();
        return WarmScaffold(
          appBar: AppBar(title: const Text('本周周报')),
          child: ListView(
            padding: const EdgeInsets.all(18),
            children: [
              SoftPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${_date(report.startDate)} - ${_date(report.endDate)}',
                      style: const TextStyle(color: muted),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      report.recordCount == 0
                          ? '这一周还没有数据'
                          : report.trendSummary,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      report.insight,
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
                    const Text('最近的你，好像...', style: TextStyle(color: muted)),
                    const SizedBox(height: 10),
                    Text(
                      state.emotionInsightText,
                      style: const TextStyle(
                        color: ink,
                        fontSize: 17,
                        height: 1.55,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SoftPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('撑过去了的证据', style: TextStyle(color: muted)),
                    const SizedBox(height: 10),
                    Text(
                      state.survivedMomentText,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: _MetricTile(
                      label: '主情绪',
                      value: report.dominantMood,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _MetricTile(
                      label: '压力源',
                      value: report.pressureSource,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              SoftPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('高频关键词', style: TextStyle(color: muted)),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: report.keywords.isEmpty
                          ? [const Chip(label: Text('还在积累中'))]
                          : report.keywords
                                .map(
                                  (word) => Chip(
                                    label: Text(word),
                                    backgroundColor: mist,
                                  ),
                                )
                                .toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              SoftPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('给你的一句话', style: TextStyle(color: muted)),
                    const SizedBox(height: 10),
                    Text(
                      report.comfortSentence,
                      style: const TextStyle(
                        color: ink,
                        fontSize: 17,
                        height: 1.55,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      report.joySource,
                      style: const TextStyle(color: muted, height: 1.5),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  String _date(DateTime date) =>
      '${date.month.toString().padLeft(2, '0')}月${date.day.toString().padLeft(2, '0')}日';
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.66),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ink.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: muted, fontSize: 12)),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
              color: ink,
              fontSize: 15,
              fontWeight: FontWeight.w700,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }
}
