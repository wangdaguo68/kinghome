import 'package:flutter/material.dart';

import '../theme.dart';
import '../widgets/shell.dart';
import 'check_in_screen.dart';
import 'future_mail_screen.dart';
import 'home_screen.dart';
import 'profile_screen.dart';
import 'resonance_screen.dart';
import 'timeline_screen.dart';

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int index = 0;

  final pages = const [
    HomeScreen(),
    CheckInScreen(),
    ResonanceScreen(),
    TimelineScreen(),
    FutureMailScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return WarmScaffold(
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        backgroundColor: paper.withValues(alpha: 0.94),
        indicatorColor: wheat.withValues(alpha: 0.34),
        onDestinationSelected: (next) => setState(() => index = next),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: '首页',
          ),
          NavigationDestination(
            icon: Icon(Icons.event_available_outlined),
            selectedIcon: Icon(Icons.event_available),
            label: '打卡',
          ),
          NavigationDestination(
            icon: Icon(Icons.mark_unread_chat_alt_outlined),
            selectedIcon: Icon(Icons.mark_unread_chat_alt),
            label: '纸条',
          ),
          NavigationDestination(
            icon: Icon(Icons.timeline_outlined),
            selectedIcon: Icon(Icons.timeline),
            label: '时间轴',
          ),
          NavigationDestination(
            icon: Icon(Icons.mail_outline),
            selectedIcon: Icon(Icons.mail),
            label: '信箱',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: '我的',
          ),
        ],
      ),
      child: IndexedStack(index: index, children: pages),
    );
  }
}
