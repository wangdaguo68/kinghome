import 'package:buxiangshuo/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows dashboard and core actions', (tester) async {
    await tester.pumpWidget(const BuxiangshuoApp());
    await tester.pumpAndSettle();

    expect(find.text('今天，你想把什么先放下来？'), findsOneWidget);
    expect(find.text('先放下来'), findsOneWidget);
    expect(find.text('最近的情绪线索'), findsOneWidget);
  });
}
