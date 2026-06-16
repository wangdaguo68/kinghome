import 'package:flutter/material.dart';

import '../main.dart';
import '../theme.dart';
import '../widgets/shell.dart';
import 'card_screen.dart';

class SummaryScreen extends StatelessWidget {
  const SummaryScreen({super.key, required this.recordId});

  final String recordId;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final record = state.recordById(recordId);
    final summary = record?.summary;
    return WarmScaffold(
      appBar: AppBar(title: const Text('今日情绪总结')),
      child: ListView(
        padding: const EdgeInsets.all(22),
        children: [
          if (summary == null)
            const SoftPanel(child: Text('总结还没有生成。请返回倾诉页后点击“结束并总结”。'))
          else ...[
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('我听见的是', style: TextStyle(color: muted)),
                  const SizedBox(height: 10),
                  Text(
                    state.heardSentence(record!),
                    style: const TextStyle(
                      color: ink,
                      fontSize: 18,
                      height: 1.55,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('情绪复盘卡', style: TextStyle(color: muted)),
                  const SizedBox(height: 12),
                  _ReviewRow(
                    label: '表面上的情绪',
                    value: summary.surfaceEmotion.isEmpty
                        ? record.moodLabel
                        : summary.surfaceEmotion,
                  ),
                  _ReviewRow(
                    label: '真正难受的点',
                    value: summary.realPainPoint.isEmpty
                        ? '有一些感受没有被好好看见。'
                        : summary.realPainPoint,
                  ),
                  _ReviewRow(
                    label: '真正需要的是',
                    value: summary.hiddenNeed.isEmpty
                        ? '被理解，也被允许慢一点。'
                        : summary.hiddenNeed,
                  ),
                  _ReviewRow(
                    label: '今晚先做一件小事',
                    value: summary.smallAction.isEmpty
                        ? '写下今天已经完成的一件事。'
                        : summary.smallAction,
                  ),
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(top: 8),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: wheat.withValues(alpha: 0.24),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Text(
                      summary.selfComfortSentence.isEmpty
                          ? summary.comfortSentence
                          : summary.selfComfortSentence,
                      style: const TextStyle(
                        color: ink,
                        fontSize: 17,
                        height: 1.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('情绪关键词', style: TextStyle(color: muted)),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: summary.keywords
                        .map(
                          (word) =>
                              Chip(label: Text(word), backgroundColor: mist),
                        )
                        .toList(),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: _InfoTile(
                          label: '情绪颜色',
                          value: summary.emotionColor,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: _InfoTile(label: '强度', value: summary.intensity),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text(
                    summary.summary,
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 18),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: wheat.withValues(alpha: 0.24),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Text(
                      summary.comfortSentence,
                      style: const TextStyle(
                        color: ink,
                        fontSize: 17,
                        height: 1.5,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            FilledButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => CardScreen(recordId: recordId),
                ),
              ),
              child: const Text('生成今日治愈卡'),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: muted, fontSize: 12)),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              color: ink,
              fontSize: 16,
              height: 1.45,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  const _InfoTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.56),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: muted, fontSize: 12)),
          const SizedBox(height: 5),
          Text(
            value,
            style: const TextStyle(color: ink, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}
