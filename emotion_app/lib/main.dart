import 'package:flutter/material.dart';

import 'app_state.dart';
import 'screens/app_shell.dart';
import 'theme.dart';

void main() {
  runApp(const BuxiangshuoApp());
}

class BuxiangshuoApp extends StatefulWidget {
  const BuxiangshuoApp({super.key});

  @override
  State<BuxiangshuoApp> createState() => _BuxiangshuoAppState();
}

class _BuxiangshuoAppState extends State<BuxiangshuoApp> {
  late final AppState state;

  @override
  void initState() {
    super.initState();
    state = AppState()..load();
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      state: state,
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        title: '不想说',
        theme: buildAppTheme(),
        home: const AppShell(),
      ),
    );
  }
}

class AppScope extends InheritedNotifier<AppState> {
  const AppScope({super.key, required AppState state, required super.child})
    : super(notifier: state);

  static AppState of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope not found');
    return scope!.notifier!;
  }
}
