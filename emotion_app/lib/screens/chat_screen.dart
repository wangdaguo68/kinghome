import 'package:flutter/material.dart';

import '../main.dart';
import '../models.dart';
import '../theme.dart';
import '../widgets/shell.dart';
import 'summary_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.recordId});

  final String recordId;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final controller = TextEditingController();

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return AnimatedBuilder(
      animation: state,
      builder: (context, _) {
        final record = state.recordById(widget.recordId);
        if (record == null) {
          return const WarmScaffold(child: Center(child: Text('记录不存在')));
        }
        return WarmScaffold(
          appBar: AppBar(
            title: Text('${record.moodEmoji} ${record.moodLabel}'),
            actions: [
              TextButton(
                onPressed: record.messages.isEmpty || state.summarizing
                    ? null
                    : () async {
                        await state.summarize(record.id);
                        if (context.mounted) {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) =>
                                  SummaryScreen(recordId: record.id),
                            ),
                          );
                        }
                      },
                child: state.summarizing
                    ? const Text('总结中')
                    : const Text('结束并总结'),
              ),
            ],
          ),
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 6, 18, 4),
                child: _ModeBar(
                  selected: record.replyMode,
                  onSelected: (mode) => state.updateReplyMode(record.id, mode),
                ),
              ),
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.fromLTRB(18, 12, 18, 18),
                  itemCount: record.messages.length + (state.sending ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == record.messages.length) {
                      return const _TypingBubble();
                    }
                    return _MessageBubble(message: record.messages[index]);
                  },
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: controller,
                          minLines: 1,
                          maxLines: 4,
                          decoration: InputDecoration(
                            hintText: '想到什么说什么',
                            filled: true,
                            fillColor: Colors.white.withValues(alpha: 0.78),
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
                      ),
                      const SizedBox(width: 10),
                      FilledButton(
                        style: FilledButton.styleFrom(
                          shape: const CircleBorder(),
                          minimumSize: const Size(52, 52),
                          padding: EdgeInsets.zero,
                        ),
                        onPressed: state.sending
                            ? null
                            : () {
                                final text = controller.text;
                                controller.clear();
                                state.sendMessage(record.id, text);
                              },
                        child: const Icon(Icons.arrow_upward),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _ModeBar extends StatelessWidget {
  const _ModeBar({required this.selected, required this.onSelected});

  final ReplyMode selected;
  final ValueChanged<ReplyMode> onSelected;

  @override
  Widget build(BuildContext context) {
    return SoftPanel(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '这次你希望我怎么回应？',
            style: TextStyle(color: muted, fontSize: 12),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ReplyMode.values.map((mode) {
              final active = selected == mode;
              return ChoiceChip(
                selected: active,
                label: Text(mode.shortLabel),
                selectedColor: wheat.withValues(alpha: 0.34),
                backgroundColor: Colors.white.withValues(alpha: 0.66),
                side: BorderSide(color: ink.withValues(alpha: 0.08)),
                onSelected: (_) => onSelected(mode),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == ChatRole.user;
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.78,
        ),
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: isUser
              ? clay.withValues(alpha: 0.38)
              : Colors.white.withValues(alpha: 0.76),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: ink.withValues(alpha: 0.06)),
        ),
        child: Text(
          message.content,
          style: const TextStyle(color: ink, height: 1.55),
        ),
      ),
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.68),
          borderRadius: BorderRadius.circular(18),
        ),
        child: const Text('正在轻轻整理你的话...', style: TextStyle(color: muted)),
      ),
    );
  }
}
