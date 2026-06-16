import 'dart:convert';

enum ChatRole { user, assistant }

enum ReplyMode { listenOnly, comfort, analysis, advice, noReasoning }

extension ReplyModeView on ReplyMode {
  String get label {
    switch (this) {
      case ReplyMode.listenOnly:
        return '只想被听见';
      case ReplyMode.comfort:
        return '想要一点安慰';
      case ReplyMode.analysis:
        return '想冷静分析';
      case ReplyMode.advice:
        return '想要具体建议';
      case ReplyMode.noReasoning:
        return '不要讲道理';
    }
  }

  String get shortLabel {
    switch (this) {
      case ReplyMode.listenOnly:
        return '听见';
      case ReplyMode.comfort:
        return '安慰';
      case ReplyMode.analysis:
        return '分析';
      case ReplyMode.advice:
        return '建议';
      case ReplyMode.noReasoning:
        return '不讲理';
    }
  }

  String get apiValue {
    switch (this) {
      case ReplyMode.listenOnly:
        return 'listen_only';
      case ReplyMode.comfort:
        return 'comfort';
      case ReplyMode.analysis:
        return 'analysis';
      case ReplyMode.advice:
        return 'advice';
      case ReplyMode.noReasoning:
        return 'no_reasoning';
    }
  }

  static ReplyMode fromApiValue(String? value) {
    switch (value) {
      case 'listen_only':
        return ReplyMode.listenOnly;
      case 'analysis':
        return ReplyMode.analysis;
      case 'advice':
        return ReplyMode.advice;
      case 'no_reasoning':
        return ReplyMode.noReasoning;
      case 'comfort':
      default:
        return ReplyMode.comfort;
    }
  }
}

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.safetyTriggered = false,
  });

  final String id;
  final ChatRole role;
  final String content;
  final DateTime createdAt;
  final bool safetyTriggered;

  Map<String, dynamic> toJson() => {
    'id': id,
    'role': role.name,
    'content': content,
    'createdAt': createdAt.toIso8601String(),
    'safetyTriggered': safetyTriggered,
  };

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] as String,
      role: (json['role'] as String) == 'assistant'
          ? ChatRole.assistant
          : ChatRole.user,
      content: json['content'] as String,
      createdAt: DateTime.parse(json['createdAt'] as String),
      safetyTriggered: json['safetyTriggered'] as bool? ?? false,
    );
  }
}

class EmotionSummary {
  const EmotionSummary({
    required this.keywords,
    required this.emotionColor,
    required this.intensity,
    required this.summary,
    required this.comfortSentence,
    this.surfaceEmotion = '',
    this.realPainPoint = '',
    this.hiddenNeed = '',
    this.smallAction = '',
    this.selfComfortSentence = '',
  });

  final List<String> keywords;
  final String emotionColor;
  final String intensity;
  final String summary;
  final String comfortSentence;
  final String surfaceEmotion;
  final String realPainPoint;
  final String hiddenNeed;
  final String smallAction;
  final String selfComfortSentence;

  Map<String, dynamic> toJson() => {
    'keywords': keywords,
    'emotionColor': emotionColor,
    'intensity': intensity,
    'summary': summary,
    'comfortSentence': comfortSentence,
    'surfaceEmotion': surfaceEmotion,
    'realPainPoint': realPainPoint,
    'hiddenNeed': hiddenNeed,
    'smallAction': smallAction,
    'selfComfortSentence': selfComfortSentence,
  };

  factory EmotionSummary.fromJson(Map<String, dynamic> json) {
    return EmotionSummary(
      keywords: List<String>.from(json['keywords'] as List? ?? const []),
      emotionColor: json['emotionColor'] as String? ?? '暖灰蓝',
      intensity: json['intensity'] as String? ?? '中度',
      summary: json['summary'] as String? ?? '',
      comfortSentence: json['comfortSentence'] as String? ?? '',
      surfaceEmotion: json['surfaceEmotion'] as String? ?? '',
      realPainPoint: json['realPainPoint'] as String? ?? '',
      hiddenNeed: json['hiddenNeed'] as String? ?? '',
      smallAction: json['smallAction'] as String? ?? '',
      selfComfortSentence: json['selfComfortSentence'] as String? ?? '',
    );
  }
}

class EmotionRecord {
  const EmotionRecord({
    required this.id,
    required this.mood,
    required this.moodLabel,
    required this.moodEmoji,
    required this.createdAt,
    this.completedAt,
    this.messages = const [],
    this.summary,
    this.cardTemplate = 'warm',
    this.cardImagePath,
    this.replyMode = ReplyMode.comfort,
  });

  final String id;
  final String mood;
  final String moodLabel;
  final String moodEmoji;
  final DateTime createdAt;
  final DateTime? completedAt;
  final List<ChatMessage> messages;
  final EmotionSummary? summary;
  final String cardTemplate;
  final String? cardImagePath;
  final ReplyMode replyMode;

  EmotionRecord copyWith({
    DateTime? completedAt,
    List<ChatMessage>? messages,
    EmotionSummary? summary,
    String? cardTemplate,
    String? cardImagePath,
    ReplyMode? replyMode,
  }) {
    return EmotionRecord(
      id: id,
      mood: mood,
      moodLabel: moodLabel,
      moodEmoji: moodEmoji,
      createdAt: createdAt,
      completedAt: completedAt ?? this.completedAt,
      messages: messages ?? this.messages,
      summary: summary ?? this.summary,
      cardTemplate: cardTemplate ?? this.cardTemplate,
      cardImagePath: cardImagePath ?? this.cardImagePath,
      replyMode: replyMode ?? this.replyMode,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'mood': mood,
    'moodLabel': moodLabel,
    'moodEmoji': moodEmoji,
    'createdAt': createdAt.toIso8601String(),
    'completedAt': completedAt?.toIso8601String(),
    'messages': messages.map((message) => message.toJson()).toList(),
    'summary': summary?.toJson(),
    'cardTemplate': cardTemplate,
    'cardImagePath': cardImagePath,
    'replyMode': replyMode.apiValue,
  };

  factory EmotionRecord.fromJson(Map<String, dynamic> json) {
    return EmotionRecord(
      id: json['id'] as String,
      mood: json['mood'] as String,
      moodLabel: json['moodLabel'] as String,
      moodEmoji: json['moodEmoji'] as String,
      createdAt: DateTime.parse(json['createdAt'] as String),
      completedAt: json['completedAt'] == null
          ? null
          : DateTime.parse(json['completedAt'] as String),
      messages: (json['messages'] as List? ?? const [])
          .map(
            (item) =>
                ChatMessage.fromJson(Map<String, dynamic>.from(item as Map)),
          )
          .toList(),
      summary: json['summary'] == null
          ? null
          : EmotionSummary.fromJson(
              Map<String, dynamic>.from(json['summary'] as Map),
            ),
      cardTemplate: json['cardTemplate'] as String? ?? 'warm',
      cardImagePath: json['cardImagePath'] as String?,
      replyMode: ReplyModeView.fromApiValue(json['replyMode'] as String?),
    );
  }
}

class FutureLetter {
  const FutureLetter({
    required this.id,
    required this.title,
    required this.content,
    required this.openAt,
    required this.createdAt,
    this.openedAt,
    this.isOpened = false,
    this.aiReflection,
    this.userReplyToPastSelf,
  });

  final String id;
  final String title;
  final String content;
  final DateTime openAt;
  final DateTime createdAt;
  final DateTime? openedAt;
  final bool isOpened;
  final String? aiReflection;
  final String? userReplyToPastSelf;

  bool get isDue => !isOpened && !openAt.isAfter(DateTime.now());

  FutureLetter copyWith({
    String? title,
    String? content,
    DateTime? openAt,
    DateTime? openedAt,
    bool? isOpened,
    String? aiReflection,
    String? userReplyToPastSelf,
  }) {
    return FutureLetter(
      id: id,
      title: title ?? this.title,
      content: content ?? this.content,
      openAt: openAt ?? this.openAt,
      createdAt: createdAt,
      openedAt: openedAt ?? this.openedAt,
      isOpened: isOpened ?? this.isOpened,
      aiReflection: aiReflection ?? this.aiReflection,
      userReplyToPastSelf: userReplyToPastSelf ?? this.userReplyToPastSelf,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'content': content,
    'openAt': openAt.toIso8601String(),
    'createdAt': createdAt.toIso8601String(),
    'openedAt': openedAt?.toIso8601String(),
    'isOpened': isOpened,
    'aiReflection': aiReflection,
    'userReplyToPastSelf': userReplyToPastSelf,
  };

  factory FutureLetter.fromJson(Map<String, dynamic> json) {
    return FutureLetter(
      id: json['id'] as String,
      title: json['title'] as String? ?? '',
      content: json['content'] as String? ?? '',
      openAt: DateTime.parse(json['openAt'] as String),
      createdAt: DateTime.parse(json['createdAt'] as String),
      openedAt: json['openedAt'] == null
          ? null
          : DateTime.parse(json['openedAt'] as String),
      isOpened: json['isOpened'] as bool? ?? false,
      aiReflection: json['aiReflection'] as String?,
      userReplyToPastSelf: json['userReplyToPastSelf'] as String?,
    );
  }
}

class WeeklyReport {
  const WeeklyReport({
    required this.startDate,
    required this.endDate,
    required this.recordCount,
    required this.dominantMood,
    required this.pressureSource,
    required this.joySource,
    required this.keywords,
    required this.trendSummary,
    required this.insight,
    required this.comfortSentence,
  });

  final DateTime startDate;
  final DateTime endDate;
  final int recordCount;
  final String dominantMood;
  final String pressureSource;
  final String joySource;
  final List<String> keywords;
  final String trendSummary;
  final String insight;
  final String comfortSentence;
}

class CheckInEntry {
  const CheckInEntry({
    required this.id,
    required this.mood,
    required this.moodLabel,
    required this.moodEmoji,
    required this.createdAt,
    this.note = '',
  });

  final String id;
  final String mood;
  final String moodLabel;
  final String moodEmoji;
  final DateTime createdAt;
  final String note;

  Map<String, dynamic> toJson() => {
    'id': id,
    'mood': mood,
    'moodLabel': moodLabel,
    'moodEmoji': moodEmoji,
    'createdAt': createdAt.toIso8601String(),
    'note': note,
  };

  factory CheckInEntry.fromJson(Map<String, dynamic> json) {
    return CheckInEntry(
      id: json['id'] as String,
      mood: json['mood'] as String,
      moodLabel: json['moodLabel'] as String,
      moodEmoji: json['moodEmoji'] as String,
      createdAt: DateTime.parse(json['createdAt'] as String),
      note: json['note'] as String? ?? '',
    );
  }
}

class ResonanceNote {
  const ResonanceNote({
    required this.id,
    required this.moodLabel,
    required this.content,
    required this.createdAt,
    this.reactions = const {},
  });

  final String id;
  final String moodLabel;
  final String content;
  final DateTime createdAt;
  final Map<String, int> reactions;

  ResonanceNote copyWith({Map<String, int>? reactions}) {
    return ResonanceNote(
      id: id,
      moodLabel: moodLabel,
      content: content,
      createdAt: createdAt,
      reactions: reactions ?? this.reactions,
    );
  }

  factory ResonanceNote.fromJson(Map<String, dynamic> json) {
    final rawReactions = Map<String, dynamic>.from(
      json['reactions'] as Map? ?? const {},
    );
    return ResonanceNote(
      id: json['id'] as String,
      moodLabel: json['mood_label'] as String? ?? '',
      content: json['content'] as String? ?? '',
      createdAt: DateTime.parse(json['created_at'] as String),
      reactions: rawReactions.map(
        (key, value) => MapEntry(key, (value as num).toInt()),
      ),
    );
  }
}

String encodeRecords(List<EmotionRecord> records) {
  return jsonEncode(records.map((record) => record.toJson()).toList());
}

List<EmotionRecord> decodeRecords(String? raw) {
  if (raw == null || raw.isEmpty) return [];
  final decoded = jsonDecode(raw) as List;
  return decoded
      .map(
        (item) =>
            EmotionRecord.fromJson(Map<String, dynamic>.from(item as Map)),
      )
      .toList();
}

String encodeLetters(List<FutureLetter> letters) {
  return jsonEncode(letters.map((letter) => letter.toJson()).toList());
}

List<FutureLetter> decodeLetters(String? raw) {
  if (raw == null || raw.isEmpty) return [];
  final decoded = jsonDecode(raw) as List;
  return decoded
      .map(
        (item) => FutureLetter.fromJson(Map<String, dynamic>.from(item as Map)),
      )
      .toList();
}

String encodeCheckIns(List<CheckInEntry> checkIns) {
  return jsonEncode(checkIns.map((entry) => entry.toJson()).toList());
}

List<CheckInEntry> decodeCheckIns(String? raw) {
  if (raw == null || raw.isEmpty) return [];
  final decoded = jsonDecode(raw) as List;
  return decoded
      .map(
        (item) => CheckInEntry.fromJson(Map<String, dynamic>.from(item as Map)),
      )
      .toList();
}

String newId() => DateTime.now().microsecondsSinceEpoch.toString();
