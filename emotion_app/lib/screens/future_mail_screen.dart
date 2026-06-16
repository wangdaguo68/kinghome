import 'package:flutter/material.dart';

import '../app_state.dart';
import '../models.dart';
import '../main.dart';
import '../theme.dart';
import '../widgets/shell.dart';

const _letterPresets = [
  _LetterPreset(title: '写给明天的我', days: 1, prompt: '明天醒来时，我希望你记得：'),
  _LetterPreset(title: '写给低谷时的我', days: 30, prompt: '如果未来某天你又觉得很难，请先看看这句话：'),
  _LetterPreset(title: '写给一年后的我', days: 365, prompt: '一年后的你，如果看到这里，我想对你说：'),
  _LetterPreset(title: '写给重新开始的我', days: 90, prompt: '如果你正在重新开始，请别忘了：'),
];

class FutureMailScreen extends StatelessWidget {
  const FutureMailScreen({super.key});

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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '未来信箱',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '把今天说不出口的话，留给未来的自己。',
                    style: TextStyle(color: muted, height: 1.55),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: _CountTile(
                          label: '待开启',
                          value: state.dueLetters.length,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _CountTile(
                          label: '未到期',
                          value: state.upcomingLetters.length,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _CountTile(
                          label: '已打开',
                          value: state.openedLetters.length,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            FilledButton.icon(
              onPressed: () => _compose(context, state),
              icon: const Icon(Icons.add),
              label: const Text('写一封信'),
            ),
            const SizedBox(height: 14),
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('可以从这里开始', style: TextStyle(color: muted)),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _letterPresets
                        .map(
                          (preset) => ActionChip(
                            avatar: const Icon(Icons.mail_outline, size: 18),
                            label: Text(preset.title),
                            onPressed: () =>
                                _compose(context, state, preset: preset),
                          ),
                        )
                        .toList(),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            if (state.dueLetters.isNotEmpty) ...[
              const Text('已经可以打开', style: TextStyle(color: muted)),
              const SizedBox(height: 10),
              ...state.dueLetters.map(
                (letter) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _LetterCard(
                    letter: letter,
                    actionLabel: '打开',
                    onTap: () => _openLetter(context, state, letter),
                  ),
                ),
              ),
            ],
            if (state.upcomingLetters.isNotEmpty) ...[
              const SizedBox(height: 4),
              const Text('还没到时间', style: TextStyle(color: muted)),
              const SizedBox(height: 10),
              ...state.upcomingLetters.map(
                (letter) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _LetterCard(
                    letter: letter,
                    actionLabel: '等待打开',
                    onTap: () => _preview(context, letter),
                  ),
                ),
              ),
            ],
            if (state.letters.isEmpty)
              const SoftPanel(
                child: Text(
                  '还没有信件。你可以先写给一个月后的自己。',
                  style: TextStyle(color: muted, height: 1.55),
                ),
              ),
          ],
        );
      },
    );
  }

  Future<void> _compose(
    BuildContext context,
    AppState state, {
    _LetterPreset? preset,
  }) async {
    final titleController = TextEditingController(
      text: preset?.title ?? '写给未来的自己',
    );
    final contentController = TextEditingController(text: preset?.prompt ?? '');
    DateTime openAt = DateTime.now().add(Duration(days: preset?.days ?? 30));
    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('写一封信'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: titleController,
                  decoration: const InputDecoration(labelText: '标题'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: contentController,
                  maxLines: 6,
                  decoration: const InputDecoration(labelText: '内容'),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: Text('打开时间：${_date(openAt)}')),
                    TextButton(
                      onPressed: () async {
                        final picked = await showDatePicker(
                          context: dialogContext,
                          firstDate: DateTime.now(),
                          lastDate: DateTime.now().add(
                            const Duration(days: 3650),
                          ),
                          initialDate: openAt,
                        );
                        if (picked != null) {
                          setState(() => openAt = picked);
                        }
                      },
                      child: const Text('选择日期'),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('保存'),
            ),
          ],
        ),
      ),
    );
    final title = titleController.text.trim();
    final content = contentController.text.trim();
    titleController.dispose();
    contentController.dispose();
    if (result != true || content.isEmpty) {
      return;
    }
    await state.addLetter(title: title, content: content, openAt: openAt);
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('这封信已经替你收好了。未来的你会知道，今天的你没有放弃。')),
    );
  }

  Future<void> _openLetter(
    BuildContext context,
    AppState state,
    FutureLetter letter,
  ) async {
    await state.openLetter(letter.id);
    if (!context.mounted) return;
    final replyController = TextEditingController(
      text: letter.userReplyToPastSelf ?? '',
    );
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('我撑到了今天'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                letter.aiReflection ?? _reflectionText(letter),
                style: const TextStyle(
                  color: ink,
                  height: 1.55,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 14),
              const Text('过去的你写下：', style: TextStyle(color: muted)),
              const SizedBox(height: 6),
              Text(letter.content, style: const TextStyle(height: 1.55)),
              const SizedBox(height: 14),
              TextField(
                controller: replyController,
                maxLines: 3,
                decoration: const InputDecoration(labelText: '现在的我想对那时的自己说'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('稍后再写'),
          ),
          FilledButton(
            onPressed: () async {
              await state.replyToPastSelf(letter.id, replyController.text);
              if (dialogContext.mounted) {
                Navigator.of(dialogContext).pop();
              }
            },
            child: const Text('收好这句话'),
          ),
        ],
      ),
    );
    replyController.dispose();
  }

  Future<void> _preview(BuildContext context, FutureLetter letter) {
    return showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(letter.title),
        content: Text(
          '${_date(letter.openAt)} 才会打开。\n\n${_previewText(letter.content)}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  String _previewText(String text) {
    if (text.length <= 60) return text;
    return '${text.substring(0, 60)}…';
  }

  String _date(DateTime date) =>
      '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';

  String _reflectionText(FutureLetter letter) {
    final days = DateTime.now().difference(letter.createdAt).inDays;
    if (days < 30) {
      return '这是 $days 天前的你。那时候你把一句话留给未来，现在你又回到了这里。';
    }
    final months = (days / 30).floor();
    return '这是 $months 个月前的你。那时候你也许很不确定，但你还是撑到了今天。';
  }
}

class _LetterCard extends StatelessWidget {
  const _LetterCard({
    required this.letter,
    required this.actionLabel,
    required this.onTap,
  });

  final FutureLetter letter;
  final String actionLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SoftPanel(
      child: InkWell(
        borderRadius: BorderRadius.circular(22),
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    letter.title,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                Text(actionLabel, style: const TextStyle(color: deepBlue)),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              letter.userReplyToPastSelf == null
                  ? letter.content
                  : '现在的我想说：${letter.userReplyToPastSelf}',
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: muted, height: 1.5),
            ),
            const SizedBox(height: 10),
            Text(
              '打开时间：${_date(letter.openAt)}',
              style: const TextStyle(color: muted, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  String _date(DateTime date) =>
      '${date.year}.${date.month.toString().padLeft(2, '0')}.${date.day.toString().padLeft(2, '0')}';
}

class _CountTile extends StatelessWidget {
  const _CountTile({required this.label, required this.value});

  final String label;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.66),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: muted, fontSize: 12)),
          const SizedBox(height: 4),
          Text(
            '$value',
            style: const TextStyle(
              color: ink,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _LetterPreset {
  const _LetterPreset({
    required this.title,
    required this.days,
    required this.prompt,
  });

  final String title;
  final int days;
  final String prompt;
}
