import 'package:flutter/material.dart';

import '../app_state.dart';
import '../main.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/shell.dart';

class CheckInScreen extends StatefulWidget {
  const CheckInScreen({super.key});

  @override
  State<CheckInScreen> createState() => _CheckInScreenState();
}

class _CheckInScreenState extends State<CheckInScreen> {
  MoodOption selectedMood = moodOptions.first;
  final noteController = TextEditingController();

  @override
  void dispose() {
    noteController.dispose();
    super.dispose();
  }

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
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          '今日打卡',
                          style: Theme.of(context).textTheme.headlineMedium,
                        ),
                      ),
                      _DayBadge(text: '连续 ${state.checkInStreakDays} 天'),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    state.hasCheckedInToday
                        ? '今天已经把自己放在心上了。'
                        : '不用写很多，留下今天的一个小坐标就好。',
                    style: const TextStyle(color: muted, height: 1.55),
                  ),
                  const SizedBox(height: 18),
                  _CalendarStrip(checkIns: state.checkIns),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('今天的底色', style: TextStyle(color: muted)),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: moodOptions.map((mood) {
                      final selected = selectedMood.mood == mood.mood;
                      return ChoiceChip(
                        selected: selected,
                        label: Text('${mood.emoji} ${mood.label}'),
                        selectedColor: wheat.withValues(alpha: 0.42),
                        backgroundColor: Colors.white.withValues(alpha: 0.7),
                        side: BorderSide(
                          color: selected
                              ? deepBlue.withValues(alpha: 0.34)
                              : ink.withValues(alpha: 0.08),
                        ),
                        onSelected: (_) => setState(() => selectedMood = mood),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: noteController,
                    maxLines: 3,
                    maxLength: 80,
                    decoration: InputDecoration(
                      hintText: '今天想记住的一句话',
                      filled: true,
                      fillColor: Colors.white.withValues(alpha: 0.64),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(18),
                        borderSide: BorderSide(
                          color: ink.withValues(alpha: 0.08),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 6),
                  FilledButton.icon(
                    onPressed: () => _checkIn(context, state),
                    icon: Icon(
                      state.hasCheckedInToday
                          ? Icons.refresh_outlined
                          : Icons.done_rounded,
                    ),
                    label: Text(state.hasCheckedInToday ? '更新今日打卡' : '完成打卡'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _RecentCheckIns(entries: state.checkIns),
          ],
        );
      },
    );
  }

  Future<void> _checkIn(BuildContext context, AppState state) async {
    await state.addCheckIn(mood: selectedMood, note: noteController.text);
    noteController.clear();
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('今天的打卡已经收好了。')));
    }
  }
}

class _DayBadge extends StatelessWidget {
  const _DayBadge({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: deepBlue.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: deepBlue,
          fontWeight: FontWeight.w700,
          fontSize: 12,
        ),
      ),
    );
  }
}

class _CalendarStrip extends StatelessWidget {
  const _CalendarStrip({required this.checkIns});

  final List<CheckInEntry> checkIns;

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    return Row(
      children: List.generate(7, (index) {
        final day = today.subtract(Duration(days: 6 - index));
        final entry = checkIns.firstWhere(
          (item) => _sameDay(item.createdAt, day),
          orElse: () => CheckInEntry(
            id: '',
            mood: '',
            moodLabel: '',
            moodEmoji: '',
            createdAt: day,
          ),
        );
        final checked = entry.id.isNotEmpty;
        return Expanded(
          child: Padding(
            padding: EdgeInsets.only(right: index == 6 ? 0 : 8),
            child: Container(
              height: 58,
              decoration: BoxDecoration(
                color: checked
                    ? clay.withValues(alpha: 0.28)
                    : Colors.white.withValues(alpha: 0.52),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: ink.withValues(alpha: 0.08)),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    checked ? entry.moodEmoji : '·',
                    style: const TextStyle(fontSize: 18),
                  ),
                  Text(
                    '${day.month}/${day.day}',
                    style: const TextStyle(color: muted, fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }

  bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;
}

class _RecentCheckIns extends StatelessWidget {
  const _RecentCheckIns({required this.entries});

  final List<CheckInEntry> entries;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const SoftPanel(
        child: Text(
          '还没有打卡记录。今天开始，系统会帮你把这些小坐标串起来。',
          style: TextStyle(color: muted, height: 1.55),
        ),
      );
    }
    return SoftPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('最近打卡', style: TextStyle(color: muted)),
          const SizedBox(height: 10),
          ...entries
              .take(5)
              .map(
                (entry) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        entry.moodEmoji,
                        style: const TextStyle(fontSize: 22),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '${_date(entry.createdAt)} · ${entry.moodLabel}',
                              style: const TextStyle(
                                color: ink,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            if (entry.note.isNotEmpty)
                              Text(
                                entry.note,
                                style: const TextStyle(
                                  color: muted,
                                  height: 1.45,
                                ),
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
        ],
      ),
    );
  }

  String _date(DateTime date) => '${date.month}月${date.day}日';
}
