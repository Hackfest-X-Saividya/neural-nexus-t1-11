import 'package:flutter/material.dart';

class AppTheme {
  // Primary deep obsidian cyber charcoal palette (From the Beginning)
  static const Color background = Color(0xFF090D14);
  static const Color surface = Color(0xFF101520);
  static const Color surfaceLight = Color(0xFF151C2C);
  static const Color border = Color(0xFF1E283C);
  
  // Signature Cyber Hacker Neon Teal / Cyan Accents (From The Beginning!)
  static const Color primaryCyan = Color(0xFF00BFA5);       // Rich Cyber Hacker Teal (#00BFA5)
  static const Color primaryCyanLight = Color(0xFF2DD4BF);  // Glowing Neon Cyan (#2DD4BF)
  static const Color primaryCyanDark = Color(0xFF00897B);   // Deep Cyber Teal (#00897B)
  
  // Backward compatibility aliases so any component referencing primaryRed maps to Cyber Teal
  static const Color primaryRed = primaryCyan;
  static const Color primaryRedLight = primaryCyanLight;
  static const Color primaryRedDark = primaryCyanDark;

  // Secondary Electric Gold / Amber (Matching the Cyber Hacker ⚡ lightning bolt)
  static const Color accentGold = Color(0xFFFFB300);
  static const Color accentGoldLight = Color(0xFFFFD54F);
  
  static const Color textPrimary = Color(0xFFECEFF4);
  static const Color textSecondary = Color(0xFF8E99A8);
  static const Color textMuted = Color(0xFF5A6372);
  static const Color statusActive = Color(0xFF00BFA5);
  static const Color statusWarning = Color(0xFFFFA000);
  static const Color statusDanger = Color(0xFFEF4444);
  static const Color cardShadow = Color(0x66000000);

  static ThemeData darkTheme = ThemeData(
    fontFamily: 'Times New Roman',
    fontFamilyFallback: const ['Times', 'serif'],
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: background,
    primaryColor: primaryCyan,
    colorScheme: const ColorScheme.dark(
      primary: primaryCyan,
      secondary: primaryCyanLight,
      surface: surface,
      onPrimary: Colors.white,
      onSurface: textPrimary,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: surface,
      foregroundColor: textPrimary,
      elevation: 0,
      centerTitle: false,
    ),
    cardTheme: CardThemeData(
      color: surface,
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: border, width: 1),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: primaryCyan,
        foregroundColor: Colors.white,
        elevation: 2,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        textStyle: const TextStyle(
          fontFamily: 'Times New Roman',
          fontSize: 15,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: textPrimary,
        side: const BorderSide(color: border, width: 1.5),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
        ),
        textStyle: const TextStyle(
          fontFamily: 'Times New Roman',
          fontSize: 14,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: surfaceLight,
      hintStyle: const TextStyle(
        fontFamily: 'Times New Roman',
        color: textMuted,
        fontSize: 14,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: border, width: 1),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: border, width: 1),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: primaryCyanLight, width: 1.8),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
    ),
  );
}
