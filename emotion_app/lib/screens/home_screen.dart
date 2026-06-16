import 'package:flutter/material.dart';

import '../app_state.dart';
import '../main.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/shell.dart';
import 'check_in_screen.dart';
import 'chat_screen.dart';
import 'future_mail_screen.dart';
import 'report_screen.dart';
import 'resonance_screen.dart';
import 'timeline_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final quickController = TextEditingController();
  MoodOption selectedMood = moodOptions.first;
  ReplyMode selectedReplyMode = ReplyMode.comfort;

  @override
  void dispose() {
    quickController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        final recent = state.records.isEmpty ? null : state.records.first;
        return ListView(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 26),
          children: [
            SoftPanel(
              padding: const EdgeInsets.fromLTRB(20, 22, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '今天，你想把什么先放下来？',
                    style: Theme.of(context).textTheme.headlineLarge,
                  ),
                  const SizedBox(height: 10),
                  Text(
                    state.homeGreeting,
                    style: const TextStyle(color: muted, height: 1.55),
                  ),
                  const SizedBox(height: 18),
                  TextField(
                    controller: quickController,
                    minLines: 3,
                    maxLines: 5,
                    decoration: InputDecoration(
                      hintText: '不用整理语言，想到什么写什么。',
                      filled: true,
                      fillColor: Colors.white.withValues(alpha: 0.72),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(22),
                        borderSide: BorderSide(
                          color: ink.withValues(alpha: 0.08),
                        ),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(22),
                        borderSide: BorderSide(
                          color: ink.withValues(alpha: 0.08),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: moodOptions.take(5).map((mood) {
                      final selected = selectedMood.mood == mood.mood;
                      return ChoiceChip(
                        selected: selected,
                        label: Text('${mood.emoji} ${mood.label}'),
                        selectedColor: wheat.withValues(alpha: 0.42),
                        backgroundColor: Colors.white.withValues(alpha: 0.66),
                        side: BorderSide(
                          color: selected
                              ? deepBlue.withValues(alpha: 0.32)
                              : ink.withValues(alpha: 0.08),
                        ),
                        onSelected: (_) => setState(() => selectedMood = mood),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 10),
                  _ReplyModeStrip(
                    selected: selectedReplyMode,
                    onSelected: (mode) =>
                        setState(() => selectedReplyMode = mode),
                  ),
                  const SizedBox(height: 14),
                  FilledButton.icon(
                    onPressed: () => _startFromInput(context, state),
                    icon: const Icon(Icons.auto_awesome),
                    label: const Text('先放下来'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            _InsightPanel(
              label: '最近的情绪线索',
              text: state.emotionInsightText,
              action: '打开周报',
              onTap: () => Navigator.of(
                context,
              ).push(MaterialPageRoute(builder: (_) => const ReportScreen())),
            ),
            const SizedBox(height: 12),
            _InsightPanel(
              label: '我撑过去的事',
              text: state.survivedMomentText,
              action: '看时间轴',
              onTap: () => Navigator.of(
                context,
              ).push(MaterialPageRoute(builder: (_) => const TimelineScreen())),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _QuietAction(
                    icon: Icons.event_available_outlined,
                    title: state.hasCheckedInToday ? '已打卡' : '打卡',
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const CheckInScreen()),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _QuietAction(
                    icon: Icons.mail_outline,
                    title: '未来信箱',
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const FutureMailScreen(),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _QuietAction(
                    icon: Icons.mark_unread_chat_alt_outlined,
                    title: '纸条',
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const ResonanceScreen(),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('最近一次记录', style: TextStyle(color: muted)),
                  const SizedBox(height: 8),
                  Text(
                    recent == null
                        ? '还没有记录。今天可以先留下一句话。'
                        : (recent.summary?.summary ??
                              '${recent.moodEmoji} ${recent.moodLabel}'),
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    recent?.summary?.comfortSentence ?? '愿意说出来，就是在给自己留一条路。',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  void _startFromInput(BuildContext context, AppState state) {
    final record = state.startRecord(
      selectedMood,
      replyMode: selectedReplyMode,
    );
    final text = quickController.text.trim();
    quickController.clear();
    Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => ChatScreen(recordId: record.id)));
    if (text.isNotEmpty) {
      state.sendMessage(record.id, text);
    }
  }
}

class _InsightPanel extends StatelessWidget {
  const _InsightPanel({
    required this.label,
    required this.text,
    required this.action,
    required this.onTap,
  });

  final String label;
  final String text;
  final String action;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SoftPanel(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: muted)),
          const SizedBox(height: 8),
          Text(
            text,
            style: const TextStyle(
              color: ink,
              fontSize: 17,
              height: 1.55,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 10),
          TextButton.icon(
            onPressed: onTap,
            icon: const Icon(Icons.arrow_forward_outlined),
            label: Text(action),
          ),
        ],
      ),
    );
  }
}

class _ReplyModeStrip extends StatelessWidget {
  const _ReplyModeStrip({required this.selected, required this.onSelected});

  final ReplyMode selected;
  final ValueChanged<ReplyMode> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: ReplyMode.values.map((mode) {
        final isSelected = selected == mode;
        return ChoiceChip(
          selected: isSelected,
          label: Text(mode.shortLabel),
          selectedColor: mist,
          backgroundColor: Colors.white.withValues(alpha: 0.58),
          side: BorderSide(color: ink.withValues(alpha: 0.08)),
          onSelected: (_) => onSelected(mode),
        );
      }).toList(),
    );
  }
}

class _QuietAction extends StatelessWidget {
  const _QuietAction({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        height: 76,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.58),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: ink.withValues(alpha: 0.08)),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: deepBlue),
            const SizedBox(height: 6),
            Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: ink,
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
