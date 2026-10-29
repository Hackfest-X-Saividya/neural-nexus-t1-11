import 'package:flutter_test/flutter_test.dart';
import 'package:neuracrime/main.dart';

void main() {
  testWidgets('Neural Crime WelcomeScreen smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const NeuralCrimeApp());

    // Verify title and main action buttons exist.
    expect(find.text('Neural Crime'), findsOneWidget);
    expect(find.text('Start Witness Interview'), findsOneWidget);
    expect(find.text('New Case'), findsOneWidget);
  });
}
