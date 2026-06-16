import 'package:shared_preferences/shared_preferences.dart';

import '../models.dart';

class LocalStore {
  static const _recordsKey = 'emotion_records_v1';
  static const _lettersKey = 'future_letters_v1';
  static const _checkInsKey = 'check_ins_v1';
  static const _userIdKey = 'anonymous_user_id_v1';
  static const _recoveryCodeKey = 'recovery_code_v1';
  static const _quotaDateKey = 'quota_date_v1';
  static const _quotaKey = 'quota_count_v1';

  Future<List<EmotionRecord>> loadRecords() async {
    final prefs = await SharedPreferences.getInstance();
    final records = decodeRecords(prefs.getString(_recordsKey));
    records.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return records;
  }

  Future<void> saveRecords(List<EmotionRecord> records) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_recordsKey, encodeRecords(records));
  }

  Future<List<FutureLetter>> loadLetters() async {
    final prefs = await SharedPreferences.getInstance();
    final letters = decodeLetters(prefs.getString(_lettersKey));
    letters.sort((a, b) => a.openAt.compareTo(b.openAt));
    return letters;
  }

  Future<void> saveLetters(List<FutureLetter> letters) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lettersKey, encodeLetters(letters));
  }

  Future<List<CheckInEntry>> loadCheckIns() async {
    final prefs = await SharedPreferences.getInstance();
    final checkIns = decodeCheckIns(prefs.getString(_checkInsKey));
    checkIns.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return checkIns;
  }

  Future<void> saveCheckIns(List<CheckInEntry> checkIns) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_checkInsKey, encodeCheckIns(checkIns));
  }

  Future<String> loadOrCreateUserId() async {
    final prefs = await SharedPreferences.getInstance();
    final existing = prefs.getString(_userIdKey);
    if (existing != null && existing.isNotEmpty) return existing;
    final id = 'anon-${DateTime.now().microsecondsSinceEpoch}';
    await prefs.setString(_userIdKey, id);
    return id;
  }

  Future<String?> loadRecoveryCode() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_recoveryCodeKey);
  }

  Future<void> saveRecoveryCode(String recoveryCode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_recoveryCodeKey, recoveryCode);
  }

  Future<int> loadQuota() async {
    final prefs = await SharedPreferences.getInstance();
    final today = _today();
    if (prefs.getString(_quotaDateKey) != today) {
      await prefs.setString(_quotaDateKey, today);
      await prefs.setInt(_quotaKey, 5);
      return 5;
    }
    return prefs.getInt(_quotaKey) ?? 5;
  }

  Future<int> consumeQuota() async {
    final prefs = await SharedPreferences.getInstance();
    final current = await loadQuota();
    final next = current > 0 ? current - 1 : 0;
    await prefs.setInt(_quotaKey, next);
    return next;
  }

  String _today() {
    final now = DateTime.now();
    return '${now.year}-${now.month}-${now.day}';
  }
}
