import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models.dart';

class ApiClient {
  ApiClient({
    this.baseUrl = const String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://39.106.115.87',
    ),
  });

  final String baseUrl;

  Future<AuthApiResult?> registerAnonymous({required String userId}) async {
    final uri = Uri.parse('$baseUrl/api/auth/anonymous');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'user_id': userId}),
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final json =
            jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return AuthApiResult(
          userId: json['user_id'] as String,
          recoveryCode: json['recovery_code'] as String,
          quotaRemaining: json['quota_remaining'] as int,
        );
      }
    } catch (_) {}
    return null;
  }

  Future<ChatApiResult> sendChat({
    required String recordId,
    required String userId,
    required String moodLabel,
    required ReplyMode replyMode,
    required String message,
  }) async {
    final uri = Uri.parse('$baseUrl/api/chat/send');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'record_id': recordId,
          'user_id': userId,
          'mood_label': moodLabel,
          'reply_mode': replyMode.apiValue,
          'message': message,
        }),
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final json =
            jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return ChatApiResult(
          reply: json['reply'] as String,
          safetyTriggered: json['safety_triggered'] as bool? ?? false,
          fallback: json['fallback'] as bool? ?? false,
          quotaExceeded: json['quota_exceeded'] as bool? ?? false,
          quotaRemaining: json['quota_remaining'] as int?,
        );
      }
    } catch (_) {
      // The UI receives a warm fallback; technical details stay out of the product surface.
    }
    return const ChatApiResult(
      reply: '我这边刚刚有点没接住，你可以再发一次。刚才的话已经先帮你放在这里了。',
      fallback: true,
    );
  }

  Future<EmotionSummary> summarize({
    required String recordId,
    required String conversationText,
  }) async {
    final uri = Uri.parse('$baseUrl/api/emotion-record/summary');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'record_id': recordId,
          'conversation_text': conversationText,
        }),
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final json =
            jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return EmotionSummary(
          keywords: List<String>.from(json['keywords'] as List? ?? const []),
          emotionColor: json['emotion_color'] as String? ?? '暖灰蓝',
          intensity: json['intensity'] as String? ?? '中度',
          summary: json['summary'] as String? ?? '你今天承受了不少情绪，也许只是需要一点安静的时间。',
          comfortSentence: json['comfort_sentence'] as String? ?? '今晚先别责怪自己了。',
          surfaceEmotion: json['surface_emotion'] as String? ?? '',
          realPainPoint: json['real_pain_point'] as String? ?? '',
          hiddenNeed: json['hidden_need'] as String? ?? '',
          smallAction: json['small_action'] as String? ?? '',
          selfComfortSentence: json['self_comfort_sentence'] as String? ?? '',
        );
      }
    } catch (_) {}
    return const EmotionSummary(
      keywords: ['疲惫', '压力', '需要被理解'],
      emotionColor: '暖灰蓝',
      intensity: '中度',
      summary: '你今天像是承受了不少压力，也有一些没有被好好看见的委屈。先允许自己慢一点。',
      comfortSentence: '今晚先别责怪自己了。',
      surfaceEmotion: '疲惫和委屈',
      realPainPoint: '努力没有被好好看见',
      hiddenNeed: '被理解，也被允许休息',
      smallAction: '写下今天完成过的一件小事',
      selfComfortSentence: '你不需要今晚就证明自己。',
    );
  }

  Future<ResonanceCreateResult> createResonanceNote({
    required String userId,
    required String moodLabel,
    required String content,
  }) async {
    final uri = Uri.parse('$baseUrl/api/resonance/notes');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_id': userId,
          'mood_label': moodLabel,
          'content': content,
        }),
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final json =
            jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        return ResonanceCreateResult(
          message: json['message'] as String? ?? '这张同频纸条已经放出去了。',
          safetyTriggered: json['safety_triggered'] as bool? ?? false,
          note: json['note'] == null
              ? null
              : ResonanceNote.fromJson(
                  Map<String, dynamic>.from(json['note'] as Map),
                ),
        );
      }
    } catch (_) {}
    return const ResonanceCreateResult(
      message: '纸条暂时没有投出去。先保留这句话，等网络稳定后再试一次。',
      failed: true,
    );
  }

  Future<ResonanceNote?> fetchResonanceNote({
    required String userId,
    String? moodLabel,
  }) async {
    final query = <String, String>{'user_id': userId};
    if (moodLabel != null && moodLabel.isNotEmpty) {
      query['mood_label'] = moodLabel;
    }
    final uri = Uri.parse(
      '$baseUrl/api/resonance/notes/next',
    ).replace(queryParameters: query);
    try {
      final response = await http.get(uri);
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final raw = utf8.decode(response.bodyBytes).trim();
        if (raw == 'null' || raw.isEmpty) return null;
        return ResonanceNote.fromJson(jsonDecode(raw) as Map<String, dynamic>);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, int>?> reactToResonanceNote({
    required String noteId,
    required String userId,
    required String reaction,
  }) async {
    final uri = Uri.parse('$baseUrl/api/resonance/notes/$noteId/react');
    try {
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'user_id': userId, 'reaction': reaction}),
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final json =
            jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
        final raw = Map<String, dynamic>.from(
          json['reactions'] as Map? ?? const {},
        );
        return raw.map((key, value) => MapEntry(key, (value as num).toInt()));
      }
    } catch (_) {}
    return null;
  }
}

class AuthApiResult {
  const AuthApiResult({
    required this.userId,
    required this.recoveryCode,
    required this.quotaRemaining,
  });

  final String userId;
  final String recoveryCode;
  final int quotaRemaining;
}

class ChatApiResult {
  const ChatApiResult({
    required this.reply,
    this.safetyTriggered = false,
    this.fallback = false,
    this.quotaExceeded = false,
    this.quotaRemaining,
  });

  final String reply;
  final bool safetyTriggered;
  final bool fallback;
  final bool quotaExceeded;
  final int? quotaRemaining;
}

class ResonanceCreateResult {
  const ResonanceCreateResult({
    required this.message,
    this.note,
    this.safetyTriggered = false,
    this.failed = false,
  });

  final String message;
  final ResonanceNote? note;
  final bool safetyTriggered;
  final bool failed;
}
