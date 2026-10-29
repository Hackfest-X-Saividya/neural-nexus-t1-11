import 'package:flutter/material.dart';
import 'screens/auth_screen.dart';
import 'screens/welcome_screen.dart';
import 'screens/witness_chat_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const NeuralCrimeApp());
}

class NeuralCrimeApp extends StatelessWidget {
  const NeuralCrimeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Neural Crime',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      initialRoute: '/',
      onGenerateRoute: (settings) {
        if (settings.name == '/') {
          return MaterialPageRoute(
            builder: (context) => const AuthScreen(),
          );
        } else if (settings.name == '/welcome') {
          return MaterialPageRoute(
            builder: (context) => const WelcomeScreen(),
          );
        } else if (settings.name == '/chat') {
          final args = settings.arguments as Map<String, dynamic>?;
          final caseId = args?['caseId'] as String? ?? 'CASE-2026-X891';
          return MaterialPageRoute(
            builder: (context) => WitnessChatScreen(caseId: caseId),
          );
        }
        return null;
      },
    );
  }
}
