import 'package:flutter/material.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

enum AuthStep {
  login,          // 1. Initial Cyber Login (Times New Roman)
  officerProfile, // 2. Police Officer Profile Form (ALWAYS ASKS THIS BEFORE STUDIO)
  policeBadge,    // 3. Attractive & Unique Holographic Police Officer Smart Badge
}

class _AuthScreenState extends State<AuthScreen> with SingleTickerProviderStateMixin {
  // Current screen state
  AuthStep _currentStep = AuthStep.login;
  bool _isNewSignUp = false;
  bool _rememberMe = true;
  bool _obscurePassword = true;
  bool _isLoading = false;

  // Account Controllers
  final _usernameController = TextEditingController(text: 'coding with kashif');
  final _passwordController = TextEditingController(text: 'password123');

  // Police Officer Profile Controllers (Times New Roman Police Records)
  final _officerNameController = TextEditingController(text: 'Inspector Vikram Rathore');
  final _badgeIdController = TextEditingController(text: 'NC-9042-FD');
  final _policeStationController = TextEditingController(text: 'Cyber Crime Police Station, Central Metro Zone');
  final _designationController = TextEditingController(text: 'Senior Forensic Investigator');
  final _roleController = TextEditingController(text: 'Lead 3D Facial Reconstructionist');
  final _contactEmailController = TextEditingController(text: 'v.rathore@police.gov.in');
  final _contactPhoneController = TextEditingController(text: '+91 98765-43210 (Ext. 402)');
  final _radioCallsignController = TextEditingController(text: 'EAGLE-402');

  late final AnimationController _glowController;

  // Cyber police color constants & Times New Roman typography
  static const Color tealAccent = Color(0xFF388E85);
  static const Color tealLight = Color(0xFF5AB6AC);
  static const Color goldAccent = Color(0xFFFFD700);
  static const String forensicFont = 'Times New Roman';

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _glowController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _officerNameController.dispose();
    _badgeIdController.dispose();
    _policeStationController.dispose();
    _designationController.dispose();
    _roleController.dispose();
    _contactEmailController.dispose();
    _contactPhoneController.dispose();
    _radioCallsignController.dispose();
    super.dispose();
  }

  Map<String, dynamic> _buildOfficerProfileData() {
    return {
      'officerName': _officerNameController.text.trim(),
      'badgeId': _badgeIdController.text.trim(),
      'policeStation': _policeStationController.text.trim(),
      'designation': _designationController.text.trim(),
      'role': _roleController.text.trim(),
      'contactEmail': _contactEmailController.text.trim(),
      'contactPhone': _contactPhoneController.text.trim(),
      'radioCallsign': _radioCallsignController.text.trim(),
      'clearanceLevel': 'Level 4 - National CJIS Forensic Access',
    };
  }

  // Called when user clicks "SIGN IN" on login card:
  // DOES NOT GO DIRECTLY TO MAIN PAGE! Asks for Police Officer Profile first!
  void _handleSignInClick() async {
    setState(() => _isLoading = true);
    await Future.delayed(const Duration(milliseconds: 400));
    if (!mounted) return;
    setState(() {
      _isLoading = false;
      _isNewSignUp = false;
      _currentStep = AuthStep.officerProfile; // PROCEED TO OFFICER PROFILE FORM
    });
  }

  // Called when user clicks "Sign Up":
  // IMMEDIATELY ASKS FOR POLICE OFFICER PROFILE!
  void _handleSignUpClick() {
    setState(() {
      _isNewSignUp = true;
      _currentStep = AuthStep.officerProfile; // PROCEED TO OFFICER PROFILE FORM
    });
  }

  // Called after officer profile is reviewed/filled:
  // Shows the attractive & unique digital Police Smart Badge!
  void _handleProfileConfirmed() async {
    setState(() => _isLoading = true);
    await Future.delayed(const Duration(milliseconds: 400));
    if (!mounted) return;
    setState(() {
      _isLoading = false;
      _currentStep = AuthStep.policeBadge; // SHOW POLICE SMART BADGE
    });
  }

  // ONLY CALLED FROM THE POLICE BADGE CARD AFTER FINAL VERIFICATION:
  void _enterMainForensicStudio() async {
    setState(() => _isLoading = true);
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    setState(() => _isLoading = false);

    // Final navigation to Main Forensic Studio with confirmed Officer Profile
    Navigator.pushReplacementNamed(
      context,
      '/chat',
      arguments: {
        'caseId': 'CASE-2026-X891',
        'officerProfile': _buildOfficerProfileData(),
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isDesktop = size.width >= 960;

    return Scaffold(
      backgroundColor: const Color(0xFF070B0E),
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 1. Fullscreen Cyber Hacker Background Image
          Image.asset(
            'assets/images/hacker_login_bg.jpg',
            fit: BoxFit.cover,
            alignment: Alignment.center,
            errorBuilder: (context, error, stackTrace) =>
                _buildFallbackHackerBackground(),
          ),

          // 2. Atmospheric Dark Vignette
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: Alignment.center,
                radius: 0.95,
                colors: [
                  Colors.black.withOpacity(0.35),
                  Colors.black.withOpacity(0.85),
                ],
              ),
            ),
          ),

          // 3. Subtle Glowing Teal Ambient Overhead Lighting
          Positioned(
            top: -100,
            left: 0,
            right: 0,
            height: 260,
            child: Container(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.topCenter,
                  radius: 1.2,
                  colors: [
                    tealAccent.withOpacity(0.20),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),

          // 4. Main Foreground UI
          SafeArea(
            child: Column(
              children: [
                // Main Centered Content
                Expanded(
                  child: Center(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
                      child: AnimatedSwitcher(
                        duration: const Duration(milliseconds: 400),
                        transitionBuilder: (child, anim) =>
                            FadeTransition(opacity: anim, child: child),
                        child: _buildCurrentStepWidget(),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // Switch between Step 1 (Login), Step 2 (Officer Profile), and Step 3 (Police Smart Badge)
  Widget _buildCurrentStepWidget() {
    switch (_currentStep) {
      case AuthStep.login:
        return _buildLoginCard();
      case AuthStep.officerProfile:
        return _buildOfficerProfileFormCard();
      case AuthStep.policeBadge:
        return _buildPoliceSmartBadgeCard();
    }
  }

  // ==========================================
  // STEP 1: LOGIN CARD (Times New Roman)
  // Clicking SIGN IN asks for Police Officer Profile next!
  // ==========================================
  Widget _buildLoginCard() {
    return ConstrainedBox(
      key: const ValueKey('login_card'),
      constraints: const BoxConstraints(maxWidth: 390),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 36.0),
        decoration: BoxDecoration(
          color: const Color(0xFF0A0F14).withOpacity(0.88),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: tealAccent.withOpacity(0.45),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.7),
              blurRadius: 30,
              spreadRadius: 5,
            ),
            BoxShadow(
              color: tealAccent.withOpacity(0.20),
              blurRadius: 25,
              spreadRadius: 2,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Cyber Header: LOGIN in Times New Roman
            const Text(
              'LOGIN',
              style: TextStyle(
                fontFamily: forensicFont,
                fontSize: 32,
                fontWeight: FontWeight.w900,
                color: Colors.white,
                letterSpacing: 4.0,
              ),
            ),
            const SizedBox(height: 8),

            // Glowing Neon Teal Underline
            AnimatedBuilder(
              animation: _glowController,
              builder: (context, child) {
                final pulse = 0.6 + (_glowController.value * 0.4);
                return Container(
                  width: 90,
                  height: 3.5,
                  decoration: BoxDecoration(
                    color: tealAccent,
                    borderRadius: BorderRadius.circular(2),
                    boxShadow: [
                      BoxShadow(
                        color: tealLight.withOpacity(pulse),
                        blurRadius: 12,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                );
              },
            ),
            const SizedBox(height: 32),

            // Username or Officer ID
            _buildUnderlineField(
              controller: _usernameController,
              hintText: 'coding with kashif',
              icon: Icons.person_outline,
            ),
            const SizedBox(height: 18),

            // Password Input Field
            TextField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              style: const TextStyle(
                fontFamily: forensicFont,
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
              cursorColor: tealLight,
              decoration: InputDecoration(
                hintText: '••••••••••••',
                hintStyle: TextStyle(
                  fontFamily: forensicFont,
                  color: Colors.white.withOpacity(0.4),
                  fontSize: 15,
                ),
                prefixIcon: const Icon(
                  Icons.lock_outline,
                  color: Colors.white70,
                  size: 20,
                ),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                    color: Colors.white60,
                    size: 19,
                  ),
                  onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                ),
                enabledBorder: const UnderlineInputBorder(
                  borderSide: BorderSide(color: tealAccent, width: 1.5),
                ),
                focusedBorder: const UnderlineInputBorder(
                  borderSide: BorderSide(color: tealLight, width: 2.2),
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 14),
              ),
            ),
            const SizedBox(height: 16),

            // Remember Me & Forgot Password Row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    SizedBox(
                      width: 22,
                      height: 22,
                      child: Checkbox(
                        value: _rememberMe,
                        activeColor: tealAccent,
                        checkColor: Colors.white,
                        side: BorderSide(color: tealAccent.withOpacity(0.7)),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                        onChanged: (val) => setState(() => _rememberMe = val ?? true),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Remember me',
                      style: TextStyle(
                        fontFamily: forensicFont,
                        color: Colors.white.withOpacity(0.8),
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
                TextButton(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Password reset dispatched to your registered police station terminal.'),
                        backgroundColor: tealAccent,
                      ),
                    );
                  },
                  style: TextButton.styleFrom(padding: EdgeInsets.zero),
                  child: const Text(
                    'Forgot password?',
                    style: TextStyle(
                      fontFamily: forensicFont,
                      color: tealLight,
                      fontSize: 13,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 28),

            // Rounded Pill "SIGN IN" Button
            // (Takes officer to verify their Police Officer Profile, NOT directly to main page!)
            SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _handleSignInClick,
                style: ElevatedButton.styleFrom(
                  backgroundColor: tealAccent,
                  foregroundColor: Colors.white,
                  elevation: 10,
                  shadowColor: tealAccent.withOpacity(0.75),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(28),
                  ),
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.2,
                          color: Colors.white,
                        ),
                      )
                    : const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            'SIGN IN',
                            style: TextStyle(
                              fontFamily: forensicFont,
                              fontSize: 16,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 2.2,
                            ),
                          ),
                          SizedBox(width: 8),
                          Icon(Icons.arrow_forward_rounded, size: 18),
                        ],
                      ),
              ),
            ),
            const SizedBox(height: 20),

            // "OR" Divider
            Row(
              children: [
                Expanded(child: Divider(color: Colors.white.withOpacity(0.15))),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 14),
                  child: Text(
                    'OR',
                    style: TextStyle(
                      fontFamily: forensicFont,
                      color: Colors.white54,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.0,
                    ),
                  ),
                ),
                Expanded(child: Divider(color: Colors.white.withOpacity(0.15))),
              ],
            ),
            const SizedBox(height: 20),

            // Continue with Google Button
            SizedBox(
              width: double.infinity,
              height: 46,
              child: OutlinedButton(
                onPressed: _isLoading ? null : _handleSignInClick,
                style: OutlinedButton.styleFrom(
                  backgroundColor: Colors.white.withOpacity(0.04),
                  side: BorderSide(
                    color: Colors.white.withOpacity(0.18),
                    width: 1.0,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24),
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Image.network(
                      'https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg',
                      width: 18,
                      height: 18,
                      errorBuilder: (ctx, err, st) => const Icon(
                        Icons.g_mobiledata,
                        color: Colors.white,
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'Continue with Google',
                      style: TextStyle(
                        fontFamily: forensicFont,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                        letterSpacing: 0.4,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 22),

            // Toggle to Sign Up (DIRECTLY ASKS FOR POLICE PROFILE)
            TextButton(
              onPressed: _handleSignUpClick,
              child: RichText(
                text: const TextSpan(
                  text: "Don't have an account? ",
                  style: TextStyle(
                    fontFamily: forensicFont,
                    color: Colors.white70,
                    fontSize: 14,
                  ),
                  children: [
                    TextSpan(
                      text: 'Sign Up',
                      style: TextStyle(
                        fontFamily: forensicFont,
                        color: tealLight,
                        fontWeight: FontWeight.w800,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ==========================================
  // STEP 2: POLICE OFFICER PROFILE FORM (Times New Roman)
  // ASKS FOR:
  // 1. Officer name and badge/ID number
  // 2. Police station
  // 3. Designation and role
  // 4. Official contact details
  // ==========================================
  Widget _buildOfficerProfileFormCard() {
    return ConstrainedBox(
      key: const ValueKey('officer_profile_form'),
      constraints: const BoxConstraints(maxWidth: 480),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 32.0, vertical: 32.0),
        decoration: BoxDecoration(
          color: const Color(0xFF090E14).withOpacity(0.92),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: tealAccent.withOpacity(0.60),
            width: 1.8,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.75),
              blurRadius: 35,
              spreadRadius: 6,
            ),
            BoxShadow(
              color: tealAccent.withOpacity(0.25),
              blurRadius: 28,
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with Police Badge Shield Icon
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: tealAccent.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: tealAccent.withOpacity(0.6)),
                  ),
                  child: const Icon(Icons.security, color: tealLight, size: 24),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _isNewSignUp ? 'POLICE OFFICER REGISTRATION' : 'VERIFY OFFICER PROFILE',
                      style: const TextStyle(
                        fontFamily: forensicFont,
                        fontSize: 18,
                        fontWeight: FontWeight.w900,
                        color: Colors.white,
                        letterSpacing: 1.5,
                      ),
                    ),
                    const Text(
                      'Required Departmental Identity Before Studio Access',
                      style: TextStyle(
                        fontFamily: forensicFont,
                        fontSize: 12,
                        color: tealLight,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 24),

            // 1. Officer Name & Badge / ID Number
            _buildProfileSectionLabel('1. OFFICER NAME & BADGE / ID NUMBER'),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  flex: 3,
                  child: _buildProfileBoxField(
                    controller: _officerNameController,
                    label: 'Officer Name',
                    icon: Icons.person,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  flex: 2,
                  child: _buildProfileBoxField(
                    controller: _badgeIdController,
                    label: 'Badge / ID No.',
                    icon: Icons.badge,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),

            // 2. Police Station
            _buildProfileSectionLabel('2. POLICE STATION & JURISDICTION'),
            const SizedBox(height: 8),
            _buildProfileBoxField(
              controller: _policeStationController,
              label: 'Police Station / Division',
              icon: Icons.local_police_outlined,
            ),
            const SizedBox(height: 18),

            // 3. Designation and Role
            _buildProfileSectionLabel('3. DESIGNATION & ROLE'),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildProfileBoxField(
                    controller: _designationController,
                    label: 'Designation',
                    icon: Icons.military_tech_outlined,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildProfileBoxField(
                    controller: _roleController,
                    label: 'Role',
                    icon: Icons.science_outlined,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),

            // 4. Official Contact Details
            _buildProfileSectionLabel('4. OFFICIAL CONTACT DETAILS'),
            const SizedBox(height: 8),
            _buildProfileBoxField(
              controller: _contactEmailController,
              label: 'Official Email (.gov / .police)',
              icon: Icons.email_outlined,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _buildProfileBoxField(
                    controller: _contactPhoneController,
                    label: 'Official Phone / Ext.',
                    icon: Icons.phone_in_talk_outlined,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildProfileBoxField(
                    controller: _radioCallsignController,
                    label: 'Radio Callsign',
                    icon: Icons.cell_tower,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 28),

            // Button to Generate Official Police ID Badge
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _handleProfileConfirmed,
                style: ElevatedButton.styleFrom(
                  backgroundColor: tealAccent,
                  foregroundColor: Colors.white,
                  elevation: 12,
                  shadowColor: tealAccent.withOpacity(0.8),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                      )
                    : const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.verified, size: 20),
                          SizedBox(width: 10),
                          Text(
                            'CONFIRM PROFILE & GENERATE BADGE',
                            style: TextStyle(
                              fontFamily: forensicFont,
                              fontSize: 14,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 1.5,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
            const SizedBox(height: 12),

            Center(
              child: TextButton(
                onPressed: () => setState(() => _currentStep = AuthStep.login),
                child: const Text(
                  'Cancel & Return to Login',
                  style: TextStyle(
                    fontFamily: forensicFont,
                    color: Colors.white60,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ==========================================
  // STEP 3: THE ATTRACTIVE & UNIQUE POLICE SMART BADGE
  // Shows full officer profile before entering studio!
  // ==========================================
  Widget _buildPoliceSmartBadgeCard() {
    return ConstrainedBox(
      key: const ValueKey('police_badge_card'),
      constraints: const BoxConstraints(maxWidth: 500),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // The Holographic Smart ID Card
          Container(
            padding: const EdgeInsets.all(26.0),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF0F1A24),
                  Color(0xFF071118),
                  Color(0xFF0C161F),
                ],
              ),
              borderRadius: BorderRadius.circular(26),
              border: Border.all(
                color: tealLight.withOpacity(0.85),
                width: 2.0,
              ),
              boxShadow: [
                BoxShadow(
                  color: tealAccent.withOpacity(0.35),
                  blurRadius: 35,
                  spreadRadius: 4,
                ),
                BoxShadow(
                  color: Colors.black.withOpacity(0.8),
                  blurRadius: 30,
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Seal Header in Times New Roman
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.black.withOpacity(0.5),
                              border: Border.all(color: goldAccent.withOpacity(0.8), width: 1.5),
                              boxShadow: [
                                BoxShadow(
                                  color: goldAccent.withOpacity(0.3),
                                  blurRadius: 10,
                                ),
                              ],
                            ),
                            child: const Icon(Icons.shield, color: goldAccent, size: 22),
                          ),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                FittedBox(
                                  fit: BoxFit.scaleDown,
                                  alignment: Alignment.centerLeft,
                                  child: Text(
                                    'POLICE FORENSIC CREDENTIALS',
                                    style: TextStyle(
                                      fontFamily: forensicFont,
                                      fontSize: 14,
                                      fontWeight: FontWeight.w900,
                                      color: Colors.white,
                                      letterSpacing: 1.2,
                                    ),
                                  ),
                                ),
                                FittedBox(
                                  fit: BoxFit.scaleDown,
                                  alignment: Alignment.centerLeft,
                                  child: Text(
                                    'DIRECTORATE OF FORENSIC INTELLIGENCE',
                                    style: TextStyle(
                                      fontFamily: forensicFont,
                                      fontSize: 9,
                                      color: tealLight,
                                      letterSpacing: 1.0,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),

                    // Official Hologram Stamp
                    Flexible(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: goldAccent.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: goldAccent.withOpacity(0.7)),
                        ),
                        child: const FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            'OFFICIAL PERSONNEL',
                            style: TextStyle(
                              fontFamily: forensicFont,
                              color: goldAccent,
                              fontSize: 8.5,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.8,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                const Divider(color: Colors.white24, height: 1),
                const SizedBox(height: 20),

                // Middle Row: Photo Hologram + Officer Details
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Biometric Officer Avatar Frame
                    Container(
                      width: 100,
                      height: 125,
                      decoration: BoxDecoration(
                        color: const Color(0xFF03080C),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: tealLight.withOpacity(0.7), width: 1.5),
                        boxShadow: [
                          BoxShadow(
                            color: tealAccent.withOpacity(0.3),
                            blurRadius: 12,
                          ),
                        ],
                      ),
                      child: Stack(
                        alignment: Alignment.center,
                        children: [
                          const Icon(Icons.person, size: 60, color: Colors.white54),
                          // Biometric Laser Scan Indicator
                          Positioned(
                            bottom: 6,
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: tealAccent.withOpacity(0.9),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const Text(
                                'BIOMETRIC OK',
                                style: TextStyle(
                                  fontFamily: forensicFont,
                                  fontSize: 8,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 18),

                    // Officer Attributes in Times New Roman
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Officer Name
                          Text(
                            _officerNameController.text.toUpperCase(),
                            style: const TextStyle(
                              fontFamily: forensicFont,
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                              color: Colors.white,
                              letterSpacing: 0.8,
                            ),
                          ),
                          const SizedBox(height: 4),

                          // Badge / ID Pill
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: tealAccent.withOpacity(0.25),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: tealLight.withOpacity(0.5)),
                            ),
                            child: Text(
                              'BADGE ID: ${_badgeIdController.text}',
                              style: const TextStyle(
                                fontFamily: forensicFont,
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                color: tealLight,
                                letterSpacing: 1.0,
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),

                          _buildBadgeDetailRow(
                            label: 'POLICE STATION',
                            value: _policeStationController.text,
                          ),
                          _buildBadgeDetailRow(
                            label: 'DESIGNATION',
                            value: _designationController.text,
                          ),
                          _buildBadgeDetailRow(
                            label: 'ROLE',
                            value: _roleController.text,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                const Divider(color: Colors.white12, height: 1),
                const SizedBox(height: 14),

                // Contact Details & Security Clearance Footer
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    // Official Contact Details
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'OFFICIAL CONTACT DETAILS',
                            style: TextStyle(
                              fontFamily: forensicFont,
                              fontSize: 10,
                              color: Colors.white54,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '📧 ${_contactEmailController.text}',
                            style: const TextStyle(
                              fontFamily: forensicFont,
                              fontSize: 12,
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          Text(
                            '📞 ${_contactPhoneController.text} | Callsign: ${_radioCallsignController.text}',
                            style: TextStyle(
                              fontFamily: forensicFont,
                              fontSize: 11,
                              color: Colors.white.withOpacity(0.85),
                            ),
                          ),
                        ],
                      ),
                    ),

                    // Security Microchip Graphics
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: Colors.black38,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: Colors.white24),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.qr_code_2, color: tealLight, size: 28),
                          SizedBox(width: 4),
                          Icon(Icons.memory, color: goldAccent, size: 22),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Primary Action: Enter 3D Forensic Studio
          SizedBox(
            width: double.infinity,
            height: 52,
            child: ElevatedButton(
              onPressed: _isLoading ? null : _enterMainForensicStudio,
              style: ElevatedButton.styleFrom(
                backgroundColor: tealAccent,
                foregroundColor: Colors.white,
                elevation: 14,
                shadowColor: tealAccent.withOpacity(0.9),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
              ),
              child: _isLoading
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.lock_open_rounded, size: 20),
                        SizedBox(width: 10),
                        Text(
                          'ENTER 3D FORENSIC STUDIO',
                          style: TextStyle(
                            fontFamily: forensicFont,
                            fontSize: 14,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 1.8,
                          ),
                        ),
                        SizedBox(width: 8),
                        Icon(Icons.arrow_forward, size: 18),
                      ],
                    ),
            ),
          ),
          const SizedBox(height: 12),

          // Secondary Action: Edit Profile
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextButton.icon(
                onPressed: () => setState(() => _currentStep = AuthStep.officerProfile),
                icon: const Icon(Icons.edit, size: 16, color: Colors.white70),
                label: const Text(
                  'Edit Officer Profile Details',
                  style: TextStyle(
                    fontFamily: forensicFont,
                    color: Colors.white70,
                    fontSize: 13,
                  ),
                ),
              ),
              const SizedBox(width: 16),
              TextButton(
                onPressed: () => setState(() => _currentStep = AuthStep.login),
                child: const Text(
                  'Return to Login',
                  style: TextStyle(
                    fontFamily: forensicFont,
                    color: tealLight,
                    fontSize: 13,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ==========================================
  // HELPER WIDGETS
  // ==========================================
  Widget _buildProfileSectionLabel(String text) {
    return Text(
      text,
      style: const TextStyle(
        fontFamily: forensicFont,
        fontSize: 11,
        color: tealLight,
        fontWeight: FontWeight.w800,
        letterSpacing: 1.2,
      ),
    );
  }

  Widget _buildProfileBoxField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontFamily: forensicFont,
            fontSize: 12,
            color: Colors.white.withOpacity(0.8),
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 6),
        TextField(
          controller: controller,
          style: const TextStyle(
            fontFamily: forensicFont,
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
          cursorColor: tealLight,
          decoration: InputDecoration(
            filled: true,
            fillColor: const Color(0xFF111822),
            prefixIcon: Icon(icon, color: tealLight, size: 18),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(color: tealAccent.withOpacity(0.35)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: tealLight, width: 1.8),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBadgeDetailRow({required String label, required String value}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4.0),
      child: RichText(
        text: TextSpan(
          text: '$label: ',
          style: const TextStyle(
            fontFamily: forensicFont,
            fontSize: 10.5,
            fontWeight: FontWeight.w700,
            color: Colors.white54,
            letterSpacing: 0.8,
          ),
          children: [
            TextSpan(
              text: value,
              style: const TextStyle(
                fontFamily: forensicFont,
                fontSize: 11.5,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                letterSpacing: 0.4,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildUnderlineField({
    required TextEditingController controller,
    required String hintText,
    required IconData icon,
  }) {
    return TextField(
      controller: controller,
      style: const TextStyle(
        fontFamily: forensicFont,
        color: Colors.white,
        fontSize: 15,
        fontWeight: FontWeight.w500,
      ),
      cursorColor: tealLight,
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: TextStyle(
          fontFamily: forensicFont,
          color: Colors.white.withOpacity(0.4),
          fontSize: 14,
        ),
        prefixIcon: Icon(icon, color: Colors.white70, size: 20),
        enabledBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: tealAccent, width: 1.5),
        ),
        focusedBorder: const UnderlineInputBorder(
          borderSide: BorderSide(color: tealLight, width: 2.2),
        ),
        contentPadding: const EdgeInsets.symmetric(vertical: 14),
      ),
    );
  }

  Widget _buildFallbackHackerBackground() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Color(0xFF031015),
            Color(0xFF071C24),
            Color(0xFF02070A),
          ],
        ),
      ),
      child: const Center(
        child: Icon(
          Icons.shield,
          size: 160,
          color: Color(0x22388E85),
        ),
      ),
    );
  }
}
