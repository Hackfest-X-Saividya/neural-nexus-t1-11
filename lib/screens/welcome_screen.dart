import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  String _currentCaseId = 'CASE-2026-X891';
  int _caseCounter = 891;

  void _createNewCase() {
    setState(() {
      _caseCounter++;
      _currentCaseId = 'CASE-2026-X$_caseCounter';
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_outline, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Text('Created and assigned new $_currentCaseId'),
          ],
        ),
        backgroundColor: AppTheme.surfaceLight,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _startWitnessInterview() {
    Navigator.pushNamed(
      context,
      '/chat',
      arguments: {'caseId': _currentCaseId},
    );
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    final isDesktop = screenSize.width > 768;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: EdgeInsets.symmetric(
              horizontal: isDesktop ? 48.0 : 24.0,
              vertical: 32.0,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // App Badge / Forensic Tag
                  Center(
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryCyan.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: AppTheme.primaryCyan.withOpacity(0.35),
                          width: 1,
                        ),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.security, size: 16, color: AppTheme.primaryCyan),
                          SizedBox(width: 8),
                          Text(
                            'FORENSIC INVESTIGATION SYSTEM',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.2,
                              color: AppTheme.primaryCyanLight,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // App Logo & Title
                  Center(
                    child: Container(
                      width: 84,
                      height: 84,
                      decoration: BoxDecoration(
                        color: AppTheme.surfaceLight,
                        borderRadius: BorderRadius.circular(22),
                        border: Border.all(color: AppTheme.border, width: 1.5),
                        boxShadow: const [
                          BoxShadow(
                            color: Colors.black26,
                            blurRadius: 16,
                            offset: Offset(0, 8),
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.fingerprint_rounded,
                        size: 50,
                        color: AppTheme.primaryCyan,
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),

                  const Text(
                    'Neural Crime',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 36,
                      fontWeight: FontWeight.bold,
                      letterSpacing: -0.5,
                      color: AppTheme.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'AI Crime Scene Sketch & Facial Composite Generator',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 15,
                      color: AppTheme.textSecondary,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 40),

                  // Case ID & Status Card
                  Container(
                    padding: const EdgeInsets.all(22),
                    decoration: BoxDecoration(
                      color: AppTheme.surface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppTheme.border),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.folder_shared_outlined,
                                    size: 18, color: AppTheme.textSecondary),
                                SizedBox(width: 8),
                                Text(
                                  'ASSIGNED CASE FILE',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: 1.0,
                                    color: AppTheme.textSecondary,
                                  ),
                                ),
                              ],
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: AppTheme.statusActive.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: AppTheme.statusActive.withOpacity(0.4),
                                  width: 1,
                                ),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  CircleAvatar(
                                    radius: 3.5,
                                    backgroundColor: AppTheme.statusActive,
                                  ),
                                  SizedBox(width: 6),
                                  Text(
                                    'ACTIVE',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: AppTheme.statusActive,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            Text(
                              _currentCaseId,
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                                fontFamily: 'monospace',
                                color: AppTheme.textPrimary,
                              ),
                            ),
                            Text(
                              'Date: ${DateTime.now().year}-${DateTime.now().month.toString().padLeft(2, '0')}-${DateTime.now().day.toString().padLeft(2, '0')}',
                              style: const TextStyle(
                                fontSize: 13,
                                color: AppTheme.textMuted,
                              ),
                            ),
                          ],
                        ),
                        const Divider(color: AppTheme.border, height: 28),
                        const Row(
                          children: [
                            Icon(Icons.info_outline,
                                size: 16, color: AppTheme.textMuted),
                            SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Initial step: Conduct witness interview to collect physical facial markers.',
                                style: TextStyle(
                                  fontSize: 12.5,
                                  color: AppTheme.textSecondary,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 32),

                  // Action Buttons
                  isDesktop
                      ? Row(
                          children: [
                            Expanded(
                              flex: 3,
                              child: ElevatedButton.icon(
                                onPressed: _startWitnessInterview,
                                icon: const Icon(Icons.record_voice_over_rounded),
                                label: const Text('Start Witness Interview'),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              flex: 2,
                              child: OutlinedButton.icon(
                                onPressed: _createNewCase,
                                icon: const Icon(Icons.add_circle_outline),
                                label: const Text('New Case'),
                              ),
                            ),
                          ],
                        )
                      : Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            ElevatedButton.icon(
                              onPressed: _startWitnessInterview,
                              icon: const Icon(Icons.record_voice_over_rounded),
                              label: const Text('Start Witness Interview'),
                            ),
                            const SizedBox(height: 14),
                            OutlinedButton.icon(
                              onPressed: _createNewCase,
                              icon: const Icon(Icons.add_circle_outline),
                              label: const Text('New Case'),
                            ),
                          ],
                        ),
                  const SizedBox(height: 48),

                  // Footer info
                  Center(
                    child: Text(
                      'Phase 1: Witness Interview & UI Architecture • Neural Nexus',
                      style: TextStyle(
                        fontSize: 12,
                        color: AppTheme.textMuted.withOpacity(0.8),
                        letterSpacing: 0.3,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

