import 'package:flutter/material.dart';
import '../services/forensic_database.dart';
import '../theme/app_theme.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  String _currentCaseId = 'CASE-2026-X891';

  @override
  void initState() {
    super.initState();
    final cases = ForensicDatabase.getAllCases();
    if (cases.isNotEmpty) {
      _currentCaseId = cases.first.caseId;
    }
  }

  void _createNewCase() {
    final newCase = ForensicDatabase.createNewCase();
    setState(() {
      _currentCaseId = newCase.caseId;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_outline, color: Colors.white, size: 20),
            const SizedBox(width: 10),
            Text('Created and assigned new ${newCase.caseId} in Database'),
          ],
        ),
        backgroundColor: AppTheme.primaryCyan,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _startWitnessInterview([String? caseId]) {
    Navigator.pushNamed(
      context,
      '/chat',
      arguments: {'caseId': caseId ?? _currentCaseId},
    ).then((_) {
      setState(() {});
    });
  }

  void _openDatabaseVaultModal() {
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setVaultState) {
          final allCases = ForensicDatabase.getAllCases();

          return AlertDialog(
            backgroundColor: const Color(0xFF101520),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: AppTheme.primaryCyan.withOpacity(0.5), width: 1.5),
            ),
            titlePadding: const EdgeInsets.fromLTRB(20, 16, 16, 10),
            contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            title: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.storage_rounded, color: AppTheme.primaryCyanLight, size: 22),
                    const SizedBox(width: 10),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Forensic Database Vault',
                          style: TextStyle(
                            fontFamily: 'Times New Roman',
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                            color: Colors.white,
                          ),
                        ),
                        Text(
                          '${allCases.length} Stored Case Files // SQLite & Persistent Storage',
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppTheme.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: Colors.white70, size: 20),
                  onPressed: () => Navigator.pop(ctx),
                ),
              ],
            ),
            content: SizedBox(
              width: 540,
              height: 440,
              child: allCases.isEmpty
                  ? const Center(
                      child: Text(
                        'No cases in database. Click "+ New Case" to create one.',
                        style: TextStyle(color: AppTheme.textSecondary),
                      ),
                    )
                  : ListView.separated(
                      itemCount: allCases.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (context, idx) {
                        final c = allCases[idx];
                        final hasImage = c.latestSketchDataUrl != null || c.latestColoredDataUrl != null;

                        return Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF141C2A),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                              color: c.caseId == _currentCaseId
                                  ? AppTheme.primaryCyan
                                  : AppTheme.border,
                              width: c.caseId == _currentCaseId ? 1.5 : 1.0,
                            ),
                          ),
                          child: Row(
                            children: [
                              // Thumbnail Preview if image exists
                              Container(
                                width: 54,
                                height: 54,
                                decoration: BoxDecoration(
                                  color: const Color(0xFF0C1019),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(color: AppTheme.border),
                                ),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(7),
                                  child: hasImage
                                      ? Image.network(
                                          (c.latestColoredDataUrl ?? c.latestSketchDataUrl)!,
                                          fit: BoxFit.cover,
                                        )
                                      : const Icon(
                                          Icons.person_pin_rounded,
                                          color: AppTheme.primaryCyanLight,
                                          size: 28,
                                        ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              // Case Details
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          c.caseId,
                                          style: const TextStyle(
                                            fontFamily: 'monospace',
                                            fontWeight: FontWeight.bold,
                                            fontSize: 14,
                                            color: AppTheme.primaryCyanLight,
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: c.status == 'VERIFIED'
                                                ? AppTheme.statusActive.withOpacity(0.2)
                                                : Colors.orange.withOpacity(0.2),
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            c.status,
                                            style: TextStyle(
                                              fontSize: 9.5,
                                              fontWeight: FontWeight.bold,
                                              color: c.status == 'VERIFIED'
                                                  ? AppTheme.statusActive
                                                  : Colors.orange,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      c.title,
                                      style: const TextStyle(
                                        fontSize: 12.5,
                                        fontWeight: FontWeight.w600,
                                        color: Colors.white,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      'Witness: ${c.witnessName} • ${c.crimeType}',
                                      style: const TextStyle(
                                        fontSize: 11,
                                        color: AppTheme.textSecondary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              // Action buttons
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    tooltip: 'Open Case',
                                    icon: const Icon(Icons.arrow_forward_rounded, color: AppTheme.primaryCyanLight),
                                    onPressed: () {
                                      Navigator.pop(ctx);
                                      setState(() {
                                        _currentCaseId = c.caseId;
                                      });
                                      _startWitnessInterview(c.caseId);
                                    },
                                  ),
                                  if (allCases.length > 1)
                                    IconButton(
                                      tooltip: 'Delete Case',
                                      icon: const Icon(Icons.delete_outline_rounded, color: Colors.redAccent, size: 20),
                                      onPressed: () {
                                        ForensicDatabase.deleteCase(c.caseId);
                                        setVaultState(() {});
                                        setState(() {
                                          _currentCaseId = ForensicDatabase.getAllCases().first.caseId;
                                        });
                                      },
                                    ),
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Close', style: TextStyle(color: AppTheme.textSecondary)),
              ),
              ElevatedButton.icon(
                onPressed: () {
                  final newCase = ForensicDatabase.createNewCase();
                  setVaultState(() {});
                  setState(() {
                    _currentCaseId = newCase.caseId;
                  });
                },
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Create New Case'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryCyan,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          );
        },
      ),
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
                            InkWell(
                              onTap: _openDatabaseVaultModal,
                              borderRadius: BorderRadius.circular(6),
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: AppTheme.primaryCyan.withOpacity(0.15),
                                  borderRadius: BorderRadius.circular(6),
                                  border: Border.all(
                                    color: AppTheme.primaryCyan.withOpacity(0.4),
                                    width: 1,
                                  ),
                                ),
                                child: const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.storage_rounded, size: 12, color: AppTheme.primaryCyanLight),
                                    SizedBox(width: 6),
                                    Text(
                                      'DATABASE VAULT',
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.bold,
                                        color: AppTheme.primaryCyanLight,
                                      ),
                                    ),
                                  ],
                                ),
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
                                onPressed: () => _startWitnessInterview(),
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
                              onPressed: () => _startWitnessInterview(),
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
                  const SizedBox(height: 14),

                  // Direct Database Vault Button
                  OutlinedButton.icon(
                    onPressed: _openDatabaseVaultModal,
                    icon: const Icon(Icons.storage_rounded, color: AppTheme.primaryCyanLight, size: 18),
                    label: const Text('Open Forensic Database Vault'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.primaryCyanLight,
                      side: BorderSide(color: AppTheme.primaryCyan.withOpacity(0.5)),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),

                  const SizedBox(height: 48),

                  // Footer info
                  Center(
                    child: Text(
                      'Forensic Storage Database Active • Neural Nexus',
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
