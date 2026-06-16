import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../main.dart';
import '../theme.dart';
import '../widgets/shell.dart';

class CardScreen extends StatefulWidget {
  const CardScreen({super.key, required this.recordId});

  final String recordId;

  @override
  State<CardScreen> createState() => _CardScreenState();
}

class _CardScreenState extends State<CardScreen> {
  final cardKey = GlobalKey();
  bool saving = false;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final record = state.recordById(widget.recordId);
    final summary = record?.summary;
    return WarmScaffold(
      appBar: AppBar(title: const Text('今日治愈卡片')),
      child: ListView(
        padding: const EdgeInsets.all(22),
        children: [
          if (record == null || summary == null)
            const SoftPanel(child: Text('还没有可生成的卡片。'))
          else ...[
            RepaintBoundary(
              key: cardKey,
              child: _HealingCard(
                date: _date(record.createdAt),
                keywords: summary.keywords,
                sentence: summary.comfortSentence,
              ),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: saving
                        ? null
                        : () => _save(context, share: false),
                    icon: const Icon(Icons.download_outlined),
                    label: Text(saving ? '生成中' : '保存'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: saving
                        ? null
                        : () => _save(context, share: true),
                    icon: const Icon(Icons.ios_share_outlined),
                    label: const Text('分享'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              'MVP 会先把卡片保存为本地 PNG 文件；相册保存权限后续可继续接入。',
              style: TextStyle(color: muted),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _save(BuildContext context, {required bool share}) async {
    final appState = AppScope.of(context);
    final messenger = ScaffoldMessenger.of(context);
    setState(() => saving = true);
    try {
      final boundary =
          cardKey.currentContext!.findRenderObject()! as RenderRepaintBoundary;
      final image = await boundary.toImage(pixelRatio: 3);
      final data = await image.toByteData(format: ui.ImageByteFormat.png);
      final bytes = data!.buffer.asUint8List();
      final dir = await getApplicationDocumentsDirectory();
      final path =
          '${dir.path}${Platform.pathSeparator}buxiangshuo-card-${DateTime.now().millisecondsSinceEpoch}.png';
      final file = File(path);
      await file.writeAsBytes(bytes);
      await appState.updateCardPath(widget.recordId, path);
      if (!context.mounted) return;
      if (share) {
        await SharePlus.instance.share(
          ShareParams(text: '来自「不想说」', files: [XFile(path)]),
        );
      } else {
        messenger.showSnackBar(SnackBar(content: Text('已保存到 $path')));
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  String _date(DateTime date) =>
      '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';
}

class _HealingCard extends StatelessWidget {
  const _HealingCard({
    required this.date,
    required this.keywords,
    required this.sentence,
  });

  final String date;
  final List<String> keywords;
  final String sentence;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 430,
      padding: const EdgeInsets.all(26),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFF0D6C6), Color(0xFFEAF1EE), Color(0xFFF2DF9E)],
        ),
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: deepBlue.withValues(alpha: 0.12),
            blurRadius: 32,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            keywords.take(3).join(' · '),
            style: const TextStyle(color: muted, fontSize: 15),
          ),
          const Spacer(),
          Text(
            sentence,
            style: const TextStyle(
              color: Color(0xFF314038),
              fontSize: 32,
              height: 1.26,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(date, style: const TextStyle(color: muted)),
              const Text('来自「不想说」', style: TextStyle(color: muted)),
            ],
          ),
        ],
      ),
    );
  }
}
