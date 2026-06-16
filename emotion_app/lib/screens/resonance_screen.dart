import 'package:flutter/material.dart';

import '../app_state.dart';
import '../main.dart';
import '../theme.dart';
import '../widgets/shell.dart';

const _presetReactions = ['我也有过', '抱抱你', '愿你今晚轻一点', '你不是一个人', '希望明天会好一点'];

class ResonanceScreen extends StatefulWidget {
  const ResonanceScreen({super.key});

  @override
  State<ResonanceScreen> createState() => _ResonanceScreenState();
}

class _ResonanceScreenState extends State<ResonanceScreen> {
  final noteController = TextEditingController();
  MoodOption selectedMood = moodOptions.first;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = AppScope.of(context);
      if (state.currentResonanceNote == null && !state.resonanceLoading) {
        state.fetchResonanceNote();
      }
    });
  }

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
                  Text(
                    '同频纸条',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    '投出一张匿名纸条，也接住一张别人的片刻。这里不开放私聊，只留下很轻的回应。',
                    style: TextStyle(color: muted, height: 1.55),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: mist.withValues(alpha: 0.72),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: const Text(
                      '今晚也有人和你一样，把说不出口的话轻轻放在这里。',
                      style: TextStyle(
                        color: deepBlue,
                        height: 1.45,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            SoftPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('投一张纸条', style: TextStyle(color: muted)),
                  const SizedBox(height: 10),
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
                    maxLines: 4,
                    maxLength: 160,
                    decoration: InputDecoration(
                      hintText: '写一句想被同频的人看见的话',
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
                    onPressed: state.resonanceSending
                        ? null
                        : () => _sendNote(context, state),
                    icon: state.resonanceSending
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send_outlined),
                    label: Text(state.resonanceSending ? '正在投出' : '投出纸条'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _IncomingNote(
              state: state,
              selectedMood: selectedMood.label,
              onRefresh: () =>
                  state.fetchResonanceNote(moodLabel: selectedMood.label),
              onReact: (reaction) => _react(context, state, reaction),
            ),
          ],
        );
      },
    );
  }

  Future<void> _sendNote(BuildContext context, AppState state) async {
    final content = noteController.text.trim();
    if (content.length < 2) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('先写下一句纸条内容。')));
      return;
    }
    final result = await state.createResonanceNote(
      moodLabel: selectedMood.label,
      content: content,
    );
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(result.message)));
    }
    if (!result.failed && !result.safetyTriggered) {
      noteController.clear();
      await state.fetchResonanceNote(moodLabel: selectedMood.label);
    }
  }

  Future<void> _react(
    BuildContext context,
    AppState state,
    String reaction,
  ) async {
    final result = await state.reactToCurrentResonanceNote(reaction);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result == null ? '回应暂时没有送达。' : '你的回应已经送到了。')),
      );
    }
  }
}

class _IncomingNote extends StatelessWidget {
  const _IncomingNote({
    required this.state,
    required this.selectedMood,
    required this.onRefresh,
    required this.onReact,
  });

  final AppState state;
  final String selectedMood;
  final VoidCallback onRefresh;
  final ValueChanged<String> onReact;

  @override
  Widget build(BuildContext context) {
    final note = state.currentResonanceNote;
    return SoftPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Expanded(
                child: Text('接住一张', style: TextStyle(color: muted)),
              ),
              TextButton.icon(
                onPressed: state.resonanceLoading ? null : onRefresh,
                icon: const Icon(Icons.refresh_outlined),
                label: const Text('换一张'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (state.resonanceLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 24),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (note == null)
            _EmptyNote(selectedMood: selectedMood)
          else ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: mist,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Text(
                note.moodLabel,
                style: const TextStyle(
                  color: deepBlue,
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text(note.content, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: _presetReactions.map((reaction) {
                final count = note.reactions[reaction] ?? 0;
                return ActionChip(
                  label: Text(count == 0 ? reaction : '$reaction · $count'),
                  avatar: const Icon(Icons.favorite_border, size: 17),
                  onPressed: state.resonanceReacting
                      ? null
                      : () => onReact(reaction),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _EmptyNote extends StatelessWidget {
  const _EmptyNote({required this.selectedMood});

  final String selectedMood;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.56),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ink.withValues(alpha: 0.08)),
      ),
      child: Text(
        '暂时还没有抽到「$selectedMood」的同频纸条。你可以先投出一张，等下一位同频的人来接住。',
        style: const TextStyle(color: muted, height: 1.55),
      ),
    );
  }
}
