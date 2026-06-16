import 'package:flutter/foundation.dart';

import 'models.dart';
import 'services/api_client.dart';
import 'services/local_store.dart';

class MoodOption {
  const MoodOption(this.mood, this.emoji, this.label);

  final String mood;
  final String emoji;
  final String label;
}

const moodOptions = [
  MoodOption('ok', '🙂', '还不错'),
  MoodOption('sad', '😔', '有点难过'),
  MoodOption('anxious', '😣', '很焦虑'),
  MoodOption('angry', '😡', '有点生气'),
  MoodOption('empty', '😶', '很空'),
  MoodOption('wronged', '😭', '很委屈'),
  MoodOption('tired', '😴', '很累'),
];

class AppState extends ChangeNotifier {
  AppState({LocalStore? store, ApiClient? api})
    : _store = store ?? LocalStore(),
      _api = api ?? ApiClient();

  final LocalStore _store;
  final ApiClient _api;

  List<EmotionRecord> records = [];
  List<FutureLetter> letters = [];
  List<CheckInEntry> checkIns = [];
  String userId = '';
  String? recoveryCode;
  int freeCountToday = 5;
  bool loading = true;
  bool sending = false;
  bool summarizing = false;
  bool resonanceLoading = false;
  bool resonanceSending = false;
  bool resonanceReacting = false;
  ResonanceNote? currentResonanceNote;

  String get homeGreeting {
    final now = DateTime.now();
    if (dueLetters.isNotEmpty) {
      return '有一封过去的你留下的信，可以打开了。';
    }
    if (records.isEmpty) {
      if (now.hour < 11) return '早上好，今天不用急着变好。';
      if (now.hour >= 21) return '如果今天很累，可以只留下一句话。';
      return '今天想留下些什么？';
    }

    final latest = records.first;
    final daysSinceLatest = _dayDiff(latest.createdAt, now);
    if (daysSinceLatest >= 3) {
      return '你不来也没关系，这里还在。';
    }
    if (daysSinceLatest == 1) {
      return '昨天你提到的感受，今天有没有轻一点？';
    }
    final streak = recordStreakDays;
    if (streak >= 2) {
      return '这是你第 $streak 天把自己放在心上。';
    }
    return '今天也可以慢慢说。';
  }

  String get homeGreetingDetail {
    if (records.isEmpty) {
      return '不用整理语言，先把说不出口的事放进这里。';
    }
    final latest = records.first;
    final summary = latest.summary;
    if (summary != null && summary.keywords.isNotEmpty) {
      return '上次你留下了「${summary.keywords.take(2).join('、')}」。这里会替你记得。';
    }
    return '系统会把这些片段整理成时间轴、周报和写给未来的信。';
  }

  int get recordStreakDays {
    if (records.isEmpty) return 0;
    final days =
        records
            .map(
              (record) => DateTime(
                record.createdAt.year,
                record.createdAt.month,
                record.createdAt.day,
              ),
            )
            .toSet()
            .toList()
          ..sort((a, b) => b.compareTo(a));
    var streak = 0;
    var cursor = DateTime.now();
    cursor = DateTime(cursor.year, cursor.month, cursor.day);
    for (final day in days) {
      if (_sameDay(day, cursor.subtract(Duration(days: streak)))) {
        streak += 1;
      } else if (streak == 0 &&
          _sameDay(day, cursor.subtract(const Duration(days: 1)))) {
        streak = 1;
      } else {
        break;
      }
    }
    return streak;
  }

  bool get hasCheckedInToday {
    final now = DateTime.now();
    return checkIns.any((entry) => _sameDay(entry.createdAt, now));
  }

  CheckInEntry? get todayCheckIn {
    final now = DateTime.now();
    for (final entry in checkIns) {
      if (_sameDay(entry.createdAt, now)) return entry;
    }
    return null;
  }

  int get checkInStreakDays {
    if (checkIns.isEmpty) return 0;
    final days =
        checkIns
            .map(
              (entry) => DateTime(
                entry.createdAt.year,
                entry.createdAt.month,
                entry.createdAt.day,
              ),
            )
            .toSet()
            .toList()
          ..sort((a, b) => b.compareTo(a));
    var streak = 0;
    var cursor = DateTime.now();
    cursor = DateTime(cursor.year, cursor.month, cursor.day);
    for (final day in days) {
      if (_sameDay(day, cursor.subtract(Duration(days: streak)))) {
        streak += 1;
      } else if (streak == 0 &&
          _sameDay(day, cursor.subtract(const Duration(days: 1)))) {
        streak = 1;
      } else {
        break;
      }
    }
    return streak;
  }

  String get timelineEvidence {
    if (records.isEmpty) {
      return '第一条记录还没开始。今天愿意留下一句，就已经算数。';
    }
    final now = DateTime.now();
    final last7 = records
        .where((record) => _dayDiff(record.createdAt, now) <= 6)
        .length;
    final hardDays = records
        .where(
          (record) => const {
            'sad',
            'anxious',
            'wronged',
            'tired',
            'empty',
          }.contains(record.mood),
        )
        .length;
    final latestHard = records
        .where(
          (record) => const {
            'sad',
            'anxious',
            'wronged',
            'tired',
            'empty',
          }.contains(record.mood),
        )
        .firstOrNull;
    final hardTail = latestHard == null
        ? '你也留下过不止一种状态。'
        : '上次你觉得${latestHard.moodLabel}，是 ${_relativeDay(latestHard.createdAt)}。你已经走到今天了。';
    return '你已经留下 ${records.length} 条记录，最近 7 天有 $last7 次把自己放在这里。'
        '其中 $hardDays 次并不轻松。$hardTail';
  }

  String heardSentence(EmotionRecord record) {
    final summary = record.summary;
    if (summary == null) {
      return '我听见的是：你已经愿意把这一刻留下来，这不是小事。';
    }
    if (summary.keywords.isNotEmpty) {
      return '我听见的是：${summary.keywords.take(2).join('、')}不是小事，'
          '你此刻更需要的可能不是立刻解决，而是先被认真接住。';
    }
    return '我听见的是：你今天承受了一些东西，也在努力让它有地方可以放。';
  }

  Future<void> load() async {
    loading = true;
    notifyListeners();
    records = await _store.loadRecords();
    letters = await _store.loadLetters();
    checkIns = await _store.loadCheckIns();
    userId = await _store.loadOrCreateUserId();
    recoveryCode = await _store.loadRecoveryCode();
    final auth = await _api.registerAnonymous(userId: userId);
    if (auth != null) {
      userId = auth.userId;
      recoveryCode = auth.recoveryCode;
      freeCountToday = auth.quotaRemaining;
      await _store.saveRecoveryCode(auth.recoveryCode);
    } else {
      freeCountToday = await _store.loadQuota();
    }
    loading = false;
    notifyListeners();
  }

  Future<CheckInEntry> addCheckIn({
    required MoodOption mood,
    required String note,
  }) async {
    final today = DateTime.now();
    final entry = CheckInEntry(
      id: newId(),
      mood: mood.mood,
      moodLabel: mood.label,
      moodEmoji: mood.emoji,
      createdAt: today,
      note: note.trim(),
    );
    final withoutToday = checkIns
        .where((item) => !_sameDay(item.createdAt, today))
        .toList();
    checkIns = [entry, ...withoutToday]
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    await _store.saveCheckIns(checkIns);
    notifyListeners();
    return entry;
  }

  String get emotionInsightText {
    final recent = _recentRecords(14);
    if (recent.length < 2) {
      return '最近的你还在慢慢留下线索。再记录几次，这里会帮你看见那些反复出现的情绪。';
    }
    final hardRecords = recent
        .where(
          (record) => const {
            'sad',
            'anxious',
            'wronged',
            'tired',
            'empty',
            'angry',
          }.contains(record.mood),
        )
        .toList();
    final lateNight = recent
        .where((record) => record.createdAt.hour >= 22)
        .length;
    final keywordCount = _keywordCounts(recent);
    final topKeywords = keywordCount.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final moodCount = <String, int>{};
    for (final record in recent) {
      moodCount[record.moodLabel] = (moodCount[record.moodLabel] ?? 0) + 1;
    }
    final moods = moodCount.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final moodText = moods.take(2).map((entry) => entry.key).join(' + ');
    final keywordText = topKeywords.take(3).map((entry) => entry.key).join('、');
    final timeText = lateNight >= 2 ? '，而且有 $lateNight 次发生在深夜' : '';
    final need = topKeywords.isEmpty ? '被认真看见一次' : '让「$keywordText」有一个可以放下来的地方';
    return '最近 14 天，你留下了 ${recent.length} 次记录，其中 ${hardRecords.length} 次并不轻松$timeText。'
        '最常出现的状态像是「$moodText」。也许你真正需要的，是$need。';
  }

  String get survivedMomentText {
    final records30 = _recentRecords(30);
    if (records30.length < 4) {
      return '等记录再多一点，这里会帮你找出那些“当时很难，后来过去了”的证据。';
    }
    final earlier = records30
        .where((record) => _dayDiff(record.createdAt, DateTime.now()) >= 7)
        .toList();
    final recent = _recentRecords(7);
    final earlierKeywords = _keywordCounts(earlier);
    if (earlierKeywords.isEmpty) {
      return '你已经留下 ${records30.length} 次记录。它们会慢慢变成你走过来的证据。';
    }
    final recentKeywords = _keywordCounts(recent);
    final candidates = earlierKeywords.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final topic = candidates.first.key;
    final before = candidates.first.value;
    final now = recentKeywords[topic] ?? 0;
    if (before >= 2 && now < before) {
      return '你曾经反复提到「$topic」$before 次。最近 7 天，它只出现了 $now 次。这不是一句鸡汤，是你慢慢撑过来的证据。';
    }
    return '有些事现在还没有完全过去，但你已经把它们说出来了 ${records30.length} 次。能留下来，本身就是在往前走。';
  }

  EmotionRecord startRecord(
    MoodOption mood, {
    ReplyMode replyMode = ReplyMode.comfort,
  }) {
    final record = EmotionRecord(
      id: newId(),
      mood: mood.mood,
      moodLabel: mood.label,
      moodEmoji: mood.emoji,
      createdAt: DateTime.now(),
      replyMode: replyMode,
    );
    records = [record, ...records];
    _persist();
    notifyListeners();
    return record;
  }

  EmotionRecord? recordById(String id) {
    for (final record in records) {
      if (record.id == id) return record;
    }
    return null;
  }

  Future<void> sendMessage(String recordId, String content) async {
    final record = recordById(recordId);
    if (record == null || content.trim().isEmpty) return;

    final userMessage = ChatMessage(
      id: newId(),
      role: ChatRole.user,
      content: content.trim(),
      createdAt: DateTime.now(),
    );
    _replaceRecord(
      record.copyWith(messages: [...record.messages, userMessage]),
    );
    sending = true;
    notifyListeners();

    final result = await _api.sendChat(
      recordId: record.id,
      userId: userId.isEmpty ? 'local-user' : userId,
      moodLabel: record.moodLabel,
      replyMode: record.replyMode,
      message: content.trim(),
    );
    if (result.quotaRemaining != null) {
      freeCountToday = result.quotaRemaining!;
    } else {
      freeCountToday = await _store.consumeQuota();
    }

    final latest = recordById(recordId);
    if (latest != null) {
      final aiMessage = ChatMessage(
        id: newId(),
        role: ChatRole.assistant,
        content: result.reply,
        createdAt: DateTime.now(),
        safetyTriggered: result.safetyTriggered,
      );
      _replaceRecord(
        latest.copyWith(messages: [...latest.messages, aiMessage]),
      );
    }
    sending = false;
    notifyListeners();
  }

  Future<EmotionSummary?> summarize(String recordId) async {
    final record = recordById(recordId);
    if (record == null || record.messages.isEmpty) return null;

    summarizing = true;
    notifyListeners();
    final text = record.messages
        .map(
          (message) =>
              '${message.role == ChatRole.user ? '用户' : 'AI'}：${message.content}',
        )
        .join('\n');
    final summary = await _api.summarize(
      recordId: record.id,
      conversationText: text,
    );
    final latest = recordById(recordId);
    if (latest != null) {
      _replaceRecord(
        latest.copyWith(summary: summary, completedAt: DateTime.now()),
      );
    }
    summarizing = false;
    notifyListeners();
    return summary;
  }

  Future<void> updateCardPath(String recordId, String path) async {
    final record = recordById(recordId);
    if (record == null) return;
    _replaceRecord(record.copyWith(cardImagePath: path));
    notifyListeners();
  }

  Future<void> updateReplyMode(String recordId, ReplyMode mode) async {
    final record = recordById(recordId);
    if (record == null) return;
    _replaceRecord(record.copyWith(replyMode: mode));
    notifyListeners();
  }

  Future<void> deleteRecord(String recordId) async {
    records = records.where((record) => record.id != recordId).toList();
    await _persist();
    notifyListeners();
  }

  Future<void> clearRecords() async {
    records = [];
    await _persist();
    notifyListeners();
  }

  List<FutureLetter> get dueLetters =>
      letters.where((letter) => letter.isDue).toList()
        ..sort((a, b) => a.openAt.compareTo(b.openAt));

  List<FutureLetter> get upcomingLetters =>
      letters.where((letter) => !letter.isDue && !letter.isOpened).toList()
        ..sort((a, b) => a.openAt.compareTo(b.openAt));

  List<FutureLetter> get openedLetters =>
      letters.where((letter) => letter.isOpened).toList()
        ..sort((a, b) => b.openedAt!.compareTo(a.openedAt!));

  Future<void> addLetter({
    required String title,
    required String content,
    required DateTime openAt,
  }) async {
    final letter = FutureLetter(
      id: newId(),
      title: title.trim().isEmpty ? '写给未来的自己' : title.trim(),
      content: content.trim(),
      openAt: openAt,
      createdAt: DateTime.now(),
    );
    letters = [letter, ...letters]
      ..sort((a, b) => a.openAt.compareTo(b.openAt));
    await _store.saveLetters(letters);
    notifyListeners();
  }

  Future<void> openLetter(String letterId) async {
    FutureLetter? target;
    for (final letter in letters) {
      if (letter.id == letterId) {
        target = letter;
        break;
      }
    }
    if (target == null) return;
    await _replaceLetter(
      target.copyWith(isOpened: true, openedAt: DateTime.now()),
    );
    notifyListeners();
  }

  Future<void> replyToPastSelf(String letterId, String reply) async {
    FutureLetter? target;
    for (final letter in letters) {
      if (letter.id == letterId) {
        target = letter;
        break;
      }
    }
    if (target == null) return;
    final reflection = _buildLetterReflection(target);
    await _replaceLetter(
      target.copyWith(
        isOpened: true,
        openedAt: target.openedAt ?? DateTime.now(),
        aiReflection: reflection,
        userReplyToPastSelf: reply.trim(),
      ),
    );
    notifyListeners();
  }

  Future<void> deleteLetter(String letterId) async {
    letters = letters.where((letter) => letter.id != letterId).toList();
    await _store.saveLetters(letters);
    notifyListeners();
  }

  Future<ResonanceCreateResult> createResonanceNote({
    required String moodLabel,
    required String content,
  }) async {
    resonanceSending = true;
    notifyListeners();
    final result = await _api.createResonanceNote(
      userId: userId.isEmpty ? 'local-user' : userId,
      moodLabel: moodLabel,
      content: content,
    );
    resonanceSending = false;
    notifyListeners();
    return result;
  }

  Future<void> fetchResonanceNote({String? moodLabel}) async {
    resonanceLoading = true;
    notifyListeners();
    currentResonanceNote = await _api.fetchResonanceNote(
      userId: userId.isEmpty ? 'local-user' : userId,
      moodLabel: moodLabel,
    );
    resonanceLoading = false;
    notifyListeners();
  }

  Future<Map<String, int>?> reactToCurrentResonanceNote(String reaction) async {
    final note = currentResonanceNote;
    if (note == null) return null;
    resonanceReacting = true;
    notifyListeners();
    final reactions = await _api.reactToResonanceNote(
      noteId: note.id,
      userId: userId.isEmpty ? 'local-user' : userId,
      reaction: reaction,
    );
    if (reactions != null) {
      currentResonanceNote = note.copyWith(reactions: reactions);
    }
    resonanceReacting = false;
    notifyListeners();
    return reactions;
  }

  WeeklyReport buildWeeklyReport() {
    final now = DateTime.now();
    final start = DateTime(
      now.year,
      now.month,
      now.day,
    ).subtract(const Duration(days: 6));
    final weekRecords =
        records.where((record) => !record.createdAt.isBefore(start)).toList()
          ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    if (weekRecords.isEmpty) {
      return WeeklyReport(
        startDate: start,
        endDate: now,
        recordCount: 0,
        dominantMood: '还没有足够记录',
        pressureSource: '暂时没有数据',
        joySource: '先从今天的一句话开始',
        keywords: const [],
        trendSummary: '这一周还没有形成稳定的情绪曲线。',
        insight: '你还在把事情慢慢说出来，这本身就是变化的开始。',
        comfortSentence: '先不用急着总结，今天愿意记录就已经算数。',
      );
    }

    final moodCount = <String, int>{};
    final keywordCount = <String, int>{};
    for (final record in weekRecords) {
      moodCount[record.moodLabel] = (moodCount[record.moodLabel] ?? 0) + 1;
      final summary = record.summary;
      if (summary != null) {
        for (final keyword in summary.keywords) {
          keywordCount[keyword] = (keywordCount[keyword] ?? 0) + 1;
        }
      }
    }

    final dominantMood = moodCount.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final topKeywords = keywordCount.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final first = weekRecords.first;
    final last = weekRecords.last;
    final pressureSource = topKeywords.isEmpty
        ? '这一周没有提炼出明显压力源'
        : '最常出现的是 ${topKeywords.first.key}';
    final joySource = weekRecords
        .map((record) => record.summary?.comfortSentence ?? '')
        .firstWhere((text) => text.isNotEmpty, orElse: () => '愿意说出来，就是在给自己松绑。');
    final summaryText =
        '这一周你一共记录了 ${weekRecords.length} 次，${dominantMood.first.key} 出现最频繁。'
        '最早的一次在 ${_formatDate(first.createdAt)}，最近一次在 ${_formatDate(last.createdAt)}。';
    final insight = topKeywords.isEmpty
        ? '你的记录开始变多了，但还在积累阶段。'
        : '你的故事正在围绕 ${topKeywords.first.key} 逐渐成形。';
    final comfort =
        weekRecords.last.summary?.comfortSentence ?? '这周你已经做得够多了，先把呼吸放慢一点。';

    return WeeklyReport(
      startDate: start,
      endDate: now,
      recordCount: weekRecords.length,
      dominantMood: dominantMood.isEmpty ? '未识别' : dominantMood.first.key,
      pressureSource: pressureSource,
      joySource: joySource,
      keywords: topKeywords.take(6).map((entry) => entry.key).toList(),
      trendSummary: summaryText,
      insight: insight,
      comfortSentence: comfort,
    );
  }

  void _replaceRecord(EmotionRecord next) {
    records =
        records.map((record) => record.id == next.id ? next : record).toList()
          ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    _persist();
  }

  Future<void> _replaceLetter(FutureLetter next) async {
    letters =
        letters.map((letter) => letter.id == next.id ? next : letter).toList()
          ..sort((a, b) => a.openAt.compareTo(b.openAt));
    await _store.saveLetters(letters);
  }

  Future<void> _persist() => _store.saveRecords(records);

  String _formatDate(DateTime date) => '${date.month}月${date.day}日';

  bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  int _dayDiff(DateTime from, DateTime to) {
    final a = DateTime(from.year, from.month, from.day);
    final b = DateTime(to.year, to.month, to.day);
    return b.difference(a).inDays;
  }

  String _relativeDay(DateTime date) {
    final diff = _dayDiff(date, DateTime.now());
    if (diff == 0) return '今天';
    if (diff == 1) return '昨天';
    return '$diff 天前';
  }

  List<EmotionRecord> _recentRecords(int days) {
    final now = DateTime.now();
    return records
        .where((record) => _dayDiff(record.createdAt, now) <= days - 1)
        .toList();
  }

  Map<String, int> _keywordCounts(List<EmotionRecord> source) {
    final counts = <String, int>{};
    for (final record in source) {
      final summary = record.summary;
      if (summary == null) continue;
      for (final keyword in summary.keywords) {
        final key = keyword.trim();
        if (key.isEmpty) continue;
        counts[key] = (counts[key] ?? 0) + 1;
      }
    }
    return counts;
  }

  String _buildLetterReflection(FutureLetter letter) {
    final diff = _dayDiff(letter.createdAt, DateTime.now());
    if (diff <= 1) {
      return '这是不久前的你。那时候你把一句话留了下来，现在你又回到了这里。';
    }
    if (diff < 30) {
      return '这是 $diff 天前的你。那时候的担心没有被否定，但今天的你已经走到了这里。';
    }
    final months = (diff / 30).floor();
    return '这是 $months 个月前的你。那时候你也许很不确定，但你还是撑到了今天。';
  }
}
