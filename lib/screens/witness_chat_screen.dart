import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../models/chat_message.dart';
import '../services/api_service.dart';
import '../services/forensic_database.dart';
import '../services/platform_bridge.dart';
import '../theme/app_theme.dart';
import '../widgets/composite_3d_viewport.dart';

class WitnessChatScreen extends StatefulWidget {
  final String caseId;

  const WitnessChatScreen({
    super.key,
    required this.caseId,
  });

  @override
  State<WitnessChatScreen> createState() => _WitnessChatScreenState();
}

class _WitnessChatScreenState extends State<WitnessChatScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _focusNode = FocusNode();

  // Active 2D Forensic Sketch & Coloured Image Data
  String? _latestSketchDataUrl;
  String? _sketchDataUrl;
  String? _coloredDataUrl;
  final ValueNotifier<String?> _sketchDataUrlNotifier = ValueNotifier<String?>(null);
  final ValueNotifier<String?> _coloredDataUrlNotifier = ValueNotifier<String?>(null);
  StreamSubscription? _sketchMsgSubscription;


  CompositeParams _currentParams = CompositeParams(
    model: 'male.glb',
    scaleX: 1.0,
    scaleY: 1.0,
    scaleZ: 1.0,
    gender: 'male',
    focus: 'face', // Default to face close-up for facial examination
    isConfirmed: false,
    activeFeature: 'Face Shape & Size',
  );

  late TabController _mobileTabController;

  // Antigravity-Style Bot Adjuster & Minimizer State
  double _chatPanelWidth = 420.0;
  bool _isChatMinimized = false;
  bool _isDraggingAdjuster = false;

  // Forensic typography: Times New Roman
  static const String forensicFont = 'Times New Roman';

  // Feature progression stages
  final List<String> _forensicStages = [
    'General Build & Gender',
    'Face Shape & Size',
    'Eyes & Eyebrows',
    'Nose Shape',
    'Mouth & Jawline',
    'Hair & Headwear',
    'Distinctive Marks',
  ];

  final List<String> _forensicQuestions = [
    'Can you recall the estimated age group, gender, and general build of the person you saw?',
    'What was the overall shape of their face? (e.g., oval, square jaw, round, face little big)',
    'How would you describe their eyes? Consider eye color, shape, and eyebrow thickness.',
    'Describe the nose shape and size (e.g., prominent bridge, flat, narrow, wide nostrils).',
    'What about their mouth, lips, or chin? Any visible facial hair (beard, mustache, stubble)?',
    'What was their hair style, length, and color? Were they wearing any hat or hood?',
    'Did you notice any distinctive features like scars, birthmarks, tattoos, piercings, or glasses?',
  ];

  int _currentQuestionIndex = 1; // Start on Face Shape question as demonstrated
  bool _isEditingLatest = false;
  String? _editingMessageId;
  bool _isProcessing = false;

  late List<ChatMessage> _messages;

  @override
  void initState() {
    super.initState();
    _mobileTabController = TabController(length: 2, vsync: this);

    _sketchMsgSubscription = PlatformBridge.listenWebMessages((data) {
      if (data['type'] == 'FORENSIC_SKETCH_READY') {
        final url = data['sketchDataUrl'] as String?;
        final style = data['style'] as String? ?? 'pencil';
        if (url != null && mounted) {
          setState(() {
            _latestSketchDataUrl = url;
            if (style == 'photo') {
              _coloredDataUrl = url;
              _coloredDataUrlNotifier.value = url;
            } else {
              _sketchDataUrl = url;
              _sketchDataUrlNotifier.value = url;
            }
          });
        }
      }
    });

    _messages = [
      ChatMessage(
        id: 'msg-0',
        text:
            'Welcome to the forensic witness interview for ${widget.caseId}. As you describe physical characteristics, the 3D model will dynamically deform its face and shape. You can tweak via chat or using the sliders below the model until you confirm.',
        sender: MessageSender.investigator,
        timestamp: DateTime.now().subtract(const Duration(minutes: 2)),
      ),
      ChatMessage(
        id: 'msg-1',
        text: _forensicQuestions[1],
        sender: MessageSender.investigator,
        timestamp: DateTime.now().subtract(const Duration(minutes: 1)),
        questionIndex: 1,
      ),
    ];
  }

  @override
  void dispose() {
    _sketchMsgSubscription?.cancel();
    _sketchDataUrlNotifier.dispose();
    _coloredDataUrlNotifier.dispose();
    _textController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    _mobileTabController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _sendMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;

    _textController.clear();

    if (_isEditingLatest && _editingMessageId != null) {
      final idx = _messages.indexWhere((m) => m.id == _editingMessageId);
      if (idx != -1) {
        setState(() {
          _messages[idx] = _messages[idx].copyWith(text: text);
          _isEditingLatest = false;
          _editingMessageId = null;
        });
      }
    } else {
      setState(() {
        _messages.add(
          ChatMessage(
            id: 'msg-${DateTime.now().millisecondsSinceEpoch}',
            text: text,
            sender: MessageSender.witness,
            timestamp: DateTime.now(),
          ),
        );
        _isProcessing = true;
      });
    }

    _scrollToBottom();

    // Call NLP parse backend or simulate deformation
    try {
      final res = await ApiService.parseDescription(
        caseId: widget.caseId,
        text: text,
        current: _currentParams,
      );

      if (mounted) {
        final model = res['model'] as String? ?? _currentParams.model;
        final sx = (res['scale_x'] as num?)?.toDouble() ?? _currentParams.scaleX;
        final sy = (res['scale_y'] as num?)?.toDouble() ?? _currentParams.scaleY;
        final sz = (res['scale_z'] as num?)?.toDouble() ?? _currentParams.scaleZ;
        final focus = res['focus'] as String? ?? _currentParams.focus;
        final beard = res['beard'] as String? ?? _currentParams.beard;
        final hair = res['hair'] as String? ?? _currentParams.hair;
        final glasses = res['glasses'] as String? ?? _currentParams.glasses;
        final isConfirmed = res['is_feature_confirmed'] as bool? ?? false;
        final anatomy = res['anatomy'] as Map<String, dynamic>?;

        setState(() {
          _isProcessing = false;
          _currentParams = _currentParams.copyWith(
            model: model,
            scaleX: sx,
            scaleY: sy,
            scaleZ: sz,
            focus: focus,
            beard: beard,
            hair: hair,
            glasses: glasses,
            isConfirmed: isConfirmed,
            jawWidth: (anatomy?['jawWidth'] as num?)?.toDouble() ?? _currentParams.jawWidth,
            chinLength: (anatomy?['chinLength'] as num?)?.toDouble() ?? _currentParams.chinLength,
            noseWidth: (anatomy?['noseWidth'] as num?)?.toDouble() ?? _currentParams.noseWidth,
            noseLength: (anatomy?['noseLength'] as num?)?.toDouble() ?? _currentParams.noseLength,
            eyeSpacing: (anatomy?['eyeSpacing'] as num?)?.toDouble() ?? _currentParams.eyeSpacing,
            eyeSize: (anatomy?['eyeSize'] as num?)?.toDouble() ?? _currentParams.eyeSize,
            lipThickness: (anatomy?['lipThickness'] as num?)?.toDouble() ?? _currentParams.lipThickness,
            mouthWidth: (anatomy?['mouthWidth'] as num?)?.toDouble() ?? _currentParams.mouthWidth,
            cheekbones: (anatomy?['cheekbones'] as num?)?.toDouble() ?? _currentParams.cheekbones,
          );

          if (isConfirmed) {
            _messages.add(
              ChatMessage(
                id: 'msg-sys-${DateTime.now().millisecondsSinceEpoch}',
                text: '✓ Feature verified and locked for this stage.',
                sender: MessageSender.system,
                timestamp: DateTime.now(),
              ),
            );

            if (_currentQuestionIndex + 1 < _forensicQuestions.length) {
              _currentQuestionIndex++;
              _currentParams = _currentParams.copyWith(
                isConfirmed: false,
                activeFeature: _forensicStages[_currentQuestionIndex],
              );
              _messages.add(
                ChatMessage(
                  id: 'msg-q-$_currentQuestionIndex',
                  text: _forensicQuestions[_currentQuestionIndex],
                  sender: MessageSender.investigator,
                  timestamp: DateTime.now().add(const Duration(milliseconds: 300)),
                  questionIndex: _currentQuestionIndex,
                ),
              );
            }
          }
        });
        _scrollToBottom();
      }
    } catch (e) {
      if (mounted) {
        _applyLocalFallback(text);
      }
    }
  }

  void _applyLocalFallback(String text) {
    final lower = text.toLowerCase();
    double newX = _currentParams.scaleX;
    double newY = _currentParams.scaleY;
    String newHair = _currentParams.hair;
    String newBeard = _currentParams.beard;

    if (lower.contains('big') || lower.contains('round') || lower.contains('wide')) {
      newX = (newX * 1.15).clamp(0.6, 2.0);
    } else if (lower.contains('thin') || lower.contains('narrow') || lower.contains('slim')) {
      newX = (newX * 0.88).clamp(0.6, 2.0);
    }

    if (lower.contains('long') || lower.contains('oval') || lower.contains('tall')) {
      newY = (newY * 1.15).clamp(0.6, 2.0);
    } else if (lower.contains('short') || lower.contains('square')) {
      newY = (newY * 0.90).clamp(0.6, 2.0);
    }

    if (lower.contains('curly') || lower.contains('afro')) {
      newHair = 'curly';
    } else if (lower.contains('bald')) {
      newHair = 'none';
    }

    if (lower.contains('beard') || lower.contains('goatee')) {
      newBeard = 'goatee';
    }

    bool confirmed = lower.contains('okay') ||
        lower.contains('ok') ||
        lower.contains('looks good') ||
        lower.contains('fine') ||
        lower.contains('confirmed');

    setState(() {
      _isProcessing = false;
      _currentParams = _currentParams.copyWith(
        scaleX: newX,
        scaleY: newY,
        hair: newHair,
        beard: newBeard,
        isConfirmed: confirmed,
      );

      if (confirmed && _currentQuestionIndex + 1 < _forensicQuestions.length) {
        _currentQuestionIndex++;
        _currentParams = _currentParams.copyWith(
          isConfirmed: false,
          activeFeature: _forensicStages[_currentQuestionIndex],
        );
        _messages.add(
          ChatMessage(
            id: 'msg-q-$_currentQuestionIndex',
            text: _forensicQuestions[_currentQuestionIndex],
            sender: MessageSender.investigator,
            timestamp: DateTime.now().add(const Duration(milliseconds: 300)),
            questionIndex: _currentQuestionIndex,
          ),
        );
      }
    });

    _scrollToBottom();

    // Auto-persist confirmed composite snapshot to Forensic Database
    ForensicDatabase.saveCompositeSnapshot(
      caseId: widget.caseId,
      params: _currentParams,
      sketchDataUrl: _sketchDataUrlNotifier.value ?? _sketchDataUrl,
      coloredDataUrl: _coloredDataUrlNotifier.value ?? _coloredDataUrl,
      markVerified: true,
    );
  }

  void _saveCurrentCompositeToDatabase() {
    final sketchUrl = _sketchDataUrlNotifier.value ?? _sketchDataUrl ?? _latestSketchDataUrl;
    final colorUrl = _coloredDataUrlNotifier.value ?? _coloredDataUrl;

    ForensicDatabase.saveCompositeSnapshot(
      caseId: widget.caseId,
      params: _currentParams,
      sketchDataUrl: sketchUrl,
      coloredDataUrl: colorUrl,
      markVerified: _currentParams.isConfirmed,
    );

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.storage_rounded, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '✓ Case ${widget.caseId} composite & assets saved to Forensic Database!',
                style: const TextStyle(fontFamily: forensicFont, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.primaryCyan,
      ),
    );
  }

  void _onConfirmFeaturePressed() {
    setState(() {
      _currentParams = _currentParams.copyWith(isConfirmed: true);
      _messages.add(
        ChatMessage(
          id: 'msg-conf-${DateTime.now().millisecondsSinceEpoch}',
          text:
              '✓ Witness confirmed ${_currentParams.activeFeature}. Proportions locked!',
          sender: MessageSender.system,
          timestamp: DateTime.now(),
        ),
      );

      if (_currentQuestionIndex + 1 < _forensicQuestions.length) {
        _currentQuestionIndex++;
        _currentParams = _currentParams.copyWith(
          isConfirmed: false,
          activeFeature: _forensicStages[_currentQuestionIndex],
        );
        _messages.add(
          ChatMessage(
            id: 'msg-q-$_currentQuestionIndex',
            text: _forensicQuestions[_currentQuestionIndex],
            sender: MessageSender.investigator,
            timestamp: DateTime.now().add(const Duration(milliseconds: 300)),
            questionIndex: _currentQuestionIndex,
          ),
        );
      }
    });

    _scrollToBottom();

    // Auto-persist confirmed composite snapshot to Forensic Database
    ForensicDatabase.saveCompositeSnapshot(
      caseId: widget.caseId,
      params: _currentParams,
      sketchDataUrl: _sketchDataUrlNotifier.value ?? _sketchDataUrl,
      coloredDataUrl: _coloredDataUrlNotifier.value ?? _coloredDataUrl,
      markVerified: true,
    );
  }

  void _saveCurrentCompositeToDatabase() {
    final sketchUrl = _sketchDataUrlNotifier.value ?? _sketchDataUrl ?? _latestSketchDataUrl;
    final colorUrl = _coloredDataUrlNotifier.value ?? _coloredDataUrl;

    ForensicDatabase.saveCompositeSnapshot(
      caseId: widget.caseId,
      params: _currentParams,
      sketchDataUrl: sketchUrl,
      coloredDataUrl: colorUrl,
      markVerified: _currentParams.isConfirmed,
    );

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.storage_rounded, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '✓ Case ${widget.caseId} composite & assets saved to Forensic Database!',
                style: const TextStyle(fontFamily: forensicFont, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.primaryCyan,
      ),
    );
  }

  void _triggerGenerateSketch({String style = 'pencil'}) {
    PlatformBridge.broadcastMessage({
      'type': 'GENERATE_FORENSIC_SKETCH',
      'style': style,
      'caseId': widget.caseId,
    });
    PlatformBridge.postToIframe({
      'type': 'GENERATE_FORENSIC_SKETCH',
      'style': style,
      'caseId': widget.caseId,
    });
  }

  void _downloadActiveImage(String activeFormat) {
    final isColor = activeFormat == 'colored';
    final url = isColor
        ? (_coloredDataUrlNotifier.value ?? _coloredDataUrl)
        : (_sketchDataUrlNotifier.value ?? _sketchDataUrl ?? _latestSketchDataUrl);

    final filename = isColor
        ? '${widget.caseId}_Forensic_Coloured_Portrait.png'
        : '${widget.caseId}_Forensic_2D_Sketch.png';

    if (url != null) {
      PlatformBridge.downloadFile(url, filename);
      _showDownloadSnackBar(filename);
    } else {
      // Direct instant download fallback through iframe engine
      PlatformBridge.broadcastMessage({
        'type': 'DIRECT_DOWNLOAD_IMAGE',
        'style': isColor ? 'photo' : 'pencil',
        'filename': filename,
        'caseId': widget.caseId,
      });
      PlatformBridge.postToIframe({
        'type': 'DIRECT_DOWNLOAD_IMAGE',
        'style': isColor ? 'photo' : 'pencil',
        'filename': filename,
        'caseId': widget.caseId,
      });
      _showDownloadSnackBar(filename);
    }
  }

  void _downloadBothImages() async {
    final sketchUrl = _sketchDataUrlNotifier.value ?? _sketchDataUrl ?? _latestSketchDataUrl;
    final colorUrl = _coloredDataUrlNotifier.value ?? _coloredDataUrl;

    final sketchFilename = '${widget.caseId}_Forensic_2D_Sketch.png';
    final colorFilename = '${widget.caseId}_Forensic_Coloured_Portrait.png';

    if (sketchUrl != null) {
      PlatformBridge.downloadFile(sketchUrl, sketchFilename);
    } else {
      PlatformBridge.broadcastMessage({
        'type': 'DIRECT_DOWNLOAD_IMAGE',
        'style': 'pencil',
        'filename': sketchFilename,
        'caseId': widget.caseId,
      });
      PlatformBridge.postToIframe({
        'type': 'DIRECT_DOWNLOAD_IMAGE',
        'style': 'pencil',
        'filename': sketchFilename,
        'caseId': widget.caseId,
      });
    }

    await Future.delayed(const Duration(milliseconds: 600));

    if (colorUrl != null) {
      PlatformBridge.downloadFile(colorUrl, colorFilename);
    } else {
      PlatformBridge.broadcastMessage({
        'type': 'DIRECT_DOWNLOAD_IMAGE',
        'style': 'photo',
        'filename': colorFilename,
        'caseId': widget.caseId,
      });
      PlatformBridge.postToIframe({
        'type': 'DIRECT_DOWNLOAD_IMAGE',
        'style': 'photo',
        'filename': colorFilename,
        'caseId': widget.caseId,
      });
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '✓ Downloaded Forensic files (${widget.caseId}_Forensic_2D_Sketch.png & Coloured Portrait)',
                style: const TextStyle(fontFamily: forensicFont, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.primaryCyan,
      ),
    );
  }

  void _showDownloadSnackBar(String filename) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle_rounded, color: Colors.white, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '✓ $filename downloaded successfully!',
                style: const TextStyle(fontFamily: forensicFont, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        backgroundColor: AppTheme.primaryCyan,
      ),
    );
  }

  void _showNotReadySnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: const TextStyle(fontFamily: forensicFont),
        ),
        backgroundColor: Colors.orange.shade800,
      ),
    );
  }

  void _onGenerateSketch() {
    _triggerGenerateSketch(style: 'pencil');
    Future.delayed(const Duration(milliseconds: 150), () {
      _triggerGenerateSketch(style: 'photo');
    });

    String activeFormat = 'sketch'; // 'sketch' or 'colored'
    String selectedSketchStyle = 'pencil'; // 'pencil', 'blueprint', 'noir'

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setModalState) {
          final isSketch = activeFormat == 'sketch';
          final activeNotifier = isSketch ? _sketchDataUrlNotifier : _coloredDataUrlNotifier;

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
                    Icon(
                      isSketch ? Icons.draw_rounded : Icons.camera_front_rounded,
                      color: AppTheme.primaryCyanLight,
                      size: 22,
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      'Forensic Identification Composite',
                      style: TextStyle(
                        fontFamily: forensicFont,
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                        color: Colors.white,
                      ),
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
              width: 460,
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    // Segmented Dual-Format Switcher: 2D Sketch vs Coloured Pic
                    Container(
                      padding: const EdgeInsets.all(4),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0C1019),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: InkWell(
                              onTap: () {
                                setModalState(() {
                                  activeFormat = 'sketch';
                                });
                                if (_sketchDataUrlNotifier.value == null) {
                                  _triggerGenerateSketch(style: selectedSketchStyle);
                                }
                              },
                              borderRadius: BorderRadius.circular(7),
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                decoration: BoxDecoration(
                                  color: isSketch
                                      ? AppTheme.primaryCyan.withOpacity(0.28)
                                      : Colors.transparent,
                                  borderRadius: BorderRadius.circular(7),
                                  border: isSketch
                                      ? Border.all(color: AppTheme.primaryCyanLight, width: 1.5)
                                      : null,
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.edit_note_rounded,
                                      size: 16,
                                      color: isSketch ? AppTheme.primaryCyanLight : AppTheme.textSecondary,
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      '✏️ 2D Sketch',
                                      style: TextStyle(
                                        fontFamily: forensicFont,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                        color: isSketch ? Colors.white : AppTheme.textSecondary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: InkWell(
                              onTap: () {
                                setModalState(() {
                                  activeFormat = 'colored';
                                });
                                _triggerGenerateSketch(style: 'photo');
                              },
                              borderRadius: BorderRadius.circular(7),
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                padding: const EdgeInsets.symmetric(vertical: 8),
                                decoration: BoxDecoration(
                                  color: !isSketch
                                      ? const Color(0xFF0284C7).withOpacity(0.35)
                                      : Colors.transparent,
                                  borderRadius: BorderRadius.circular(7),
                                  border: !isSketch
                                      ? Border.all(color: const Color(0xFF38BDF8), width: 1.5)
                                      : null,
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(
                                      Icons.palette_rounded,
                                      size: 16,
                                      color: !isSketch ? const Color(0xFF38BDF8) : AppTheme.textSecondary,
                                    ),
                                    const SizedBox(width: 6),
                                    Text(
                                      '🎨 Coloured Pic',
                                      style: TextStyle(
                                        fontFamily: forensicFont,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 13,
                                        color: !isSketch ? Colors.white : AppTheme.textSecondary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),

                    // Sub-controls / Style selector
                    if (isSketch)
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            _buildSketchStyleChip(
                              label: '✏️ Pencil Sketch',
                              styleKey: 'pencil',
                              selectedStyle: selectedSketchStyle,
                              onTap: () {
                                setModalState(() => selectedSketchStyle = 'pencil');
                                _triggerGenerateSketch(style: 'pencil');
                              },
                            ),
                            const SizedBox(width: 8),
                            _buildSketchStyleChip(
                              label: '📐 Blueprint',
                              styleKey: 'blueprint',
                              selectedStyle: selectedSketchStyle,
                              onTap: () {
                                setModalState(() => selectedSketchStyle = 'blueprint');
                                _triggerGenerateSketch(style: 'blueprint');
                              },
                            ),
                            const SizedBox(width: 8),
                            _buildSketchStyleChip(
                              label: '🖤 Noir Contrast',
                              styleKey: 'noir',
                              selectedStyle: selectedSketchStyle,
                              onTap: () {
                                setModalState(() => selectedSketchStyle = 'noir');
                                _triggerGenerateSketch(style: 'noir');
                              },
                            ),
                          ],
                        ),
                      )
                    else
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0284C7).withOpacity(0.15),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: const Color(0xFF38BDF8).withOpacity(0.35)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Icon(Icons.camera_alt_outlined, size: 14, color: Color(0xFF38BDF8)),
                            SizedBox(width: 6),
                            Text(
                              '3D Studio Coloured Composite • Natural Lighting & Full Color',
                              style: TextStyle(
                                fontFamily: forensicFont,
                                fontSize: 11.5,
                                color: Color(0xFFBAE6FD),
                              ),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: 14),

                    // Square High-Resolution Preview Frame (360x360)
                    Container(
                      width: 360,
                      height: 360,
                      decoration: BoxDecoration(
                        color: isSketch ? Colors.white : const Color(0xFF141A26),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: isSketch ? Colors.black87 : const Color(0xFF38BDF8).withOpacity(0.6),
                          width: 2,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: (isSketch ? AppTheme.primaryCyan : const Color(0xFF0284C7)).withOpacity(0.25),
                            blurRadius: 16,
                            spreadRadius: 2,
                          ),
                        ],
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: ValueListenableBuilder<String?>(
                          valueListenable: activeNotifier,
                          builder: (context, activeUrl, _) {
                            final displayUrl = isSketch
                                ? (activeUrl ?? _sketchDataUrl ?? _latestSketchDataUrl)
                                : (activeUrl ?? _coloredDataUrl);

                            if (displayUrl != null) {
                              return Stack(
                                children: [
                                  Image.network(
                                    displayUrl,
                                    key: ValueKey(displayUrl),
                                    width: 360,
                                    height: 360,
                                    fit: BoxFit.cover,
                                  ),
                                  Positioned(
                                    top: 10,
                                    right: 10,
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: Colors.black.withOpacity(0.75),
                                        borderRadius: BorderRadius.circular(4),
                                        border: Border.all(
                                          color: isSketch ? AppTheme.primaryCyanLight : const Color(0xFF38BDF8),
                                          width: 1,
                                        ),
                                      ),
                                      child: Text(
                                        isSketch ? '2D SKETCH' : 'COLOURED PIC',
                                        style: TextStyle(
                                          fontFamily: forensicFont,
                                          fontSize: 10,
                                          fontWeight: FontWeight.bold,
                                          color: isSketch ? AppTheme.primaryCyanLight : const Color(0xFF38BDF8),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              );
                            }

                            return Container(
                              color: const Color(0xFF141A26),
                              child: Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    CircularProgressIndicator(
                                      color: isSketch ? AppTheme.primaryCyan : const Color(0xFF38BDF8),
                                      strokeWidth: 2.5,
                                    ),
                                    const SizedBox(height: 14),
                                    Text(
                                      isSketch
                                          ? 'Extracting 2D Forensic Linework\nfrom 3D Model...'
                                          : 'Rendering Studio 3D Coloured Portrait\nfrom 3D Composite...',
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        fontFamily: forensicFont,
                                        fontSize: 13,
                                        color: isSketch ? AppTheme.primaryCyanLight : const Color(0xFF38BDF8),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),

                    // Metadata Pill
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF141C2A),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppTheme.primaryCyan.withOpacity(0.3)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Case: ${widget.caseId}',
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.bold,
                              fontSize: 12,
                              color: AppTheme.primaryCyanLight,
                            ),
                          ),
                          Text(
                            'Model: ${_currentParams.model.split('.').first.toUpperCase()} (${_currentParams.gender})',
                            style: const TextStyle(
                              fontFamily: forensicFont,
                              fontSize: 12,
                              color: AppTheme.textSecondary,
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppTheme.primaryCyan.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              _currentParams.isConfirmed ? 'VERIFIED ✓' : 'ACTIVE STAGE',
                              style: const TextStyle(
                                fontFamily: forensicFont,
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryCyanLight,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Close', style: TextStyle(color: AppTheme.textSecondary)),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  _saveCurrentCompositeToDatabase();
                },
                icon: const Icon(Icons.storage_rounded, size: 16),
                label: const Text('Save to DB'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.primaryCyanLight,
                  side: BorderSide(color: AppTheme.primaryCyan.withOpacity(0.6)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
              OutlinedButton.icon(
                onPressed: () {
                  _downloadBothImages();
                },
                icon: const Icon(Icons.file_download_outlined, size: 16),
                label: const Text('Download Both (.PNG)'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF38BDF8),
                  side: const BorderSide(color: Color(0xFF0284C7)),
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
              ElevatedButton.icon(
                onPressed: () {
                  _downloadActiveImage(activeFormat);
                },
                icon: const Icon(Icons.download_rounded, size: 18),
                label: Text(
                  isSketch ? 'Download 2D Sketch (.PNG)' : 'Download Coloured Pic (.PNG)',
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isSketch ? AppTheme.primaryCyan : const Color(0xFF0284C7),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  elevation: 4,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSketchStyleChip({
    required String label,
    required String styleKey,
    required String selectedStyle,
    required VoidCallback onTap,
  }) {
    final isSelected = selectedStyle == styleKey;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryCyan.withOpacity(0.25) : const Color(0xFF141C2A),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSelected ? AppTheme.primaryCyanLight : AppTheme.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: forensicFont,
            fontSize: 11.5,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            color: isSelected ? AppTheme.primaryCyanLight : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }

  void _startEditingLatestAnswer(ChatMessage message) {
    setState(() {
      _isEditingLatest = true;
      _editingMessageId = message.id;
      _textController.text = message.text;
    });
    _focusNode.requestFocus();
  }

  void _onMicrophonePressed() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF101520),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: AppTheme.primaryCyan.withOpacity(0.4)),
        ),
        title: const Row(
          children: [
            Icon(Icons.mic_rounded, color: AppTheme.primaryCyanLight),
            SizedBox(width: 10),
            Text('Audio Interview Input', style: TextStyle(fontFamily: forensicFont)),
          ],
        ),
        content: const Text(
          'Live speech-to-text recording is ready for hardware microphone streaming. Please ensure microphone permissions are granted.',
          style: TextStyle(fontFamily: forensicFont, fontSize: 13),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Understood', style: TextStyle(color: AppTheme.primaryCyanLight)),
          ),
        ],
      ),
    );
  }

  String? get _latestWitnessMessageId {
    for (int i = _messages.length - 1; i >= 0; i--) {
      if (_messages[i].isWitness) {
        return _messages[i].id;
      }
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;
    final isWideScreen = screenSize.width >= 960;

    return Scaffold(
      backgroundColor: AppTheme.background, // Deep obsidian cyber background (#090D14)
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D121C),
        elevation: 0,
        shape: Border(
          bottom: BorderSide(
            color: AppTheme.primaryCyan.withOpacity(0.35),
            width: 1.2,
          ),
        ),
        title: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: AppTheme.primaryCyan.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppTheme.primaryCyanLight.withOpacity(0.7)),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primaryCyan.withOpacity(0.3),
                    blurRadius: 8,
                  ),
                ],
              ),
              child: const Icon(Icons.psychology_rounded, color: AppTheme.primaryCyanLight, size: 18),
            ),
            const SizedBox(width: 10),
            const Text(
              'Witness Interview & 3D Composite',
              style: TextStyle(
                fontFamily: forensicFont,
                fontSize: 17,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
                color: Colors.white,
              ),
            ),
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: AppTheme.primaryCyan.withOpacity(0.18),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: AppTheme.primaryCyanLight.withOpacity(0.7)),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primaryCyan.withOpacity(0.25),
                    blurRadius: 8,
                  ),
                ],
              ),
              child: Text(
                widget.caseId,
                style: const TextStyle(
                  fontSize: 11,
                  fontFamily: 'monospace',
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primaryCyanLight,
                  letterSpacing: 1.0,
                ),
              ),
            ),
          ],
        ),
        bottom: !isWideScreen
            ? TabBar(
                controller: _mobileTabController,
                indicatorColor: AppTheme.primaryCyan,
                labelColor: AppTheme.primaryCyanLight,
                unselectedLabelColor: AppTheme.textSecondary,
                tabs: const [
                  Tab(icon: Icon(Icons.chat_bubble_outline), text: 'Interview'),
                  Tab(icon: Icon(Icons.view_in_ar_rounded), text: '3D Preview'),
                ],
              )
            : null,
      ),
      body: SafeArea(
        child: isWideScreen
            ? Padding(
                padding: const EdgeInsets.all(14.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // 1. LEFT COLUMN: Chat Bot (Minimizable & Resizable via Adjuster)
                    AnimatedContainer(
                      duration: _isDraggingAdjuster
                          ? Duration.zero
                          : const Duration(milliseconds: 220),
                      curve: Curves.easeOutCubic,
                      width: _isChatMinimized ? 52.0 : _chatPanelWidth,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: _isChatMinimized
                            ? _buildMinimizedBotDock()
                            : Container(
                                width: _chatPanelWidth,
                                decoration: BoxDecoration(
                                  color: const Color(0xFF101520),
                                  borderRadius: BorderRadius.circular(16),
                                  border: Border.all(
                                    color: AppTheme.primaryCyan.withOpacity(0.35),
                                    width: 1.2,
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: Colors.black.withOpacity(0.45),
                                      blurRadius: 16,
                                      offset: const Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: _buildChatColumn(),
                              ),
                      ),
                    ),

                    // 2. ANTIGRAVITY-STYLE BOT ADJUSTER (DRAGGABLE SPLITTER RESIZER)
                    _buildBotAdjuster(screenWidth: screenSize.width),

                    // 3. RIGHT COLUMN: 3D Model Viewport (Takes Remaining Width)
                    Expanded(
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFF101520),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: AppTheme.primaryCyan.withOpacity(0.35),
                            width: 1.2,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.45),
                              blurRadius: 16,
                            ),
                          ],
                        ),
                        child: Composite3DViewport(
                          params: _currentParams,
                          onParamsChanged: (newParams) {
                            setState(() {
                              _currentParams = newParams;
                            });
                          },
                          onConfirmPressed: _onConfirmFeaturePressed,
                          onGenerateSketchPressed: _onGenerateSketch,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            : TabBarView(
                controller: _mobileTabController,
                children: [
                  _buildChatColumn(),
                  Padding(
                    padding: const EdgeInsets.all(12.0),
                    child: Composite3DViewport(
                      params: _currentParams,
                      onParamsChanged: (newParams) {
                        setState(() {
                          _currentParams = newParams;
                        });
                      },
                      onConfirmPressed: _onConfirmFeaturePressed,
                      onGenerateSketchPressed: _onGenerateSketch,
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  // ==========================================
  // ANTIGRAVITY-STYLE BOT ADJUSTER (RESIZER DIVIDER)
  // Drag left/right to resize; double click or click chevron to minimize/expand!
  // ==========================================
  Widget _buildBotAdjuster({required double screenWidth}) {
    return MouseRegion(
      cursor: SystemMouseCursors.resizeColumn,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onHorizontalDragStart: (_) {
          setState(() => _isDraggingAdjuster = true);
        },
        onHorizontalDragUpdate: (details) {
          setState(() {
            if (_isChatMinimized) {
              if (details.delta.dx > 6) {
                _isChatMinimized = false;
                _chatPanelWidth = 380.0;
              }
            } else {
              _chatPanelWidth += details.delta.dx;
              if (_chatPanelWidth < 220) {
                _isChatMinimized = true;
              }
              _chatPanelWidth = _chatPanelWidth.clamp(260.0, screenWidth * 0.65);
            }
          });
        },
        onHorizontalDragEnd: (_) {
          setState(() => _isDraggingAdjuster = false);
        },
        onDoubleTap: () {
          setState(() {
            _isChatMinimized = !_isChatMinimized;
          });
        },
        child: Container(
          width: 18,
          margin: const EdgeInsets.symmetric(horizontal: 2),
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Vertical Divider Line (Cyber Cyan Glow on Drag/Hover)
              AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                width: _isDraggingAdjuster ? 3.5 : 2.0,
                decoration: BoxDecoration(
                  color: _isDraggingAdjuster
                      ? AppTheme.primaryCyanLight
                      : AppTheme.border.withOpacity(0.8),
                  borderRadius: BorderRadius.circular(2),
                  boxShadow: _isDraggingAdjuster
                      ? [
                          BoxShadow(
                            color: AppTheme.primaryCyan.withOpacity(0.8),
                            blurRadius: 10,
                            spreadRadius: 2,
                          ),
                        ]
                      : null,
                ),
              ),

              // Centered Grip Handle with Antigravity Dots
              AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                height: 52,
                width: _isDraggingAdjuster ? 14 : 10,
                decoration: BoxDecoration(
                  color: _isDraggingAdjuster
                      ? AppTheme.primaryCyan
                      : const Color(0xFF151C2C),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: _isDraggingAdjuster
                        ? AppTheme.primaryCyanLight
                        : AppTheme.primaryCyan.withOpacity(0.5),
                    width: 1.2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: _isDraggingAdjuster
                          ? AppTheme.primaryCyan.withOpacity(0.5)
                          : Colors.black.withOpacity(0.5),
                      blurRadius: _isDraggingAdjuster ? 8 : 4,
                    ),
                  ],
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 3.5,
                        height: 3.5,
                        decoration: BoxDecoration(
                          color: _isDraggingAdjuster ? Colors.white : AppTheme.primaryCyanLight,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Container(
                        width: 3.5,
                        height: 3.5,
                        decoration: BoxDecoration(
                          color: _isDraggingAdjuster ? Colors.white : AppTheme.primaryCyanLight,
                          shape: BoxShape.circle,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Container(
                        width: 3.5,
                        height: 3.5,
                        decoration: BoxDecoration(
                          color: _isDraggingAdjuster ? Colors.white : AppTheme.primaryCyanLight,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ==========================================
  // MINIMIZED DOCKED BOT SIDEBAR
  // ==========================================
  Widget _buildMinimizedBotDock() {
    return Tooltip(
      message: 'Click to expand Witness Bot',
      child: InkWell(
        onTap: () {
          setState(() {
            _isChatMinimized = false;
          });
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          width: 52,
          decoration: BoxDecoration(
            color: const Color(0xFF101520),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: AppTheme.primaryCyan.withOpacity(0.5),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: AppTheme.primaryCyan.withOpacity(0.18),
                blurRadius: 12,
              ),
            ],
          ),
          child: Column(
            children: [
              const SizedBox(height: 16),
              // Glowing Cyan Expand Circle Button
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: AppTheme.primaryCyan.withOpacity(0.2),
                  shape: BoxShape.circle,
                  border: Border.all(color: AppTheme.primaryCyanLight.withOpacity(0.7)),
                  boxShadow: [
                    BoxShadow(
                      color: AppTheme.primaryCyan.withOpacity(0.3),
                      blurRadius: 8,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.keyboard_double_arrow_right_rounded,
                  color: AppTheme.primaryCyanLight,
                  size: 20,
                ),
              ),
              const SizedBox(height: 12),
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: AppTheme.statusActive,
                  shape: BoxShape.circle,
                ),
              ),
              const Spacer(),
              RotatedBox(
                quarterTurns: 3,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Text(
                      'WITNESS BOT',
                      style: TextStyle(
                        fontFamily: forensicFont,
                        fontSize: 12,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 2.2,
                        color: AppTheme.primaryCyanLight,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryCyan.withOpacity(0.25),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: AppTheme.primaryCyan.withOpacity(0.5)),
                      ),
                      child: Text(
                        '${_messages.length}',
                        style: const TextStyle(
                          fontFamily: forensicFont,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              const Icon(
                Icons.drag_indicator,
                color: AppTheme.primaryCyanLight,
                size: 18,
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }

  // ==========================================
  // FULL EXPANDED CHAT COLUMN (Cyber Teal Theme)
  // ==========================================
  Widget _buildChatColumn() {
    final latestWitnessId = _latestWitnessMessageId;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Top Interview Header with Cyber Teal Accent & Quick Minimize
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFF131926),
            border: Border(
              bottom: BorderSide(color: AppTheme.primaryCyan.withOpacity(0.35)),
            ),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: const [
                  Icon(
                    Icons.record_voice_over_outlined,
                    size: 18,
                    color: AppTheme.primaryCyanLight,
                  ),
                  SizedBox(width: 8),
                  Text(
                    'WITNESS INTERVIEW',
                    style: TextStyle(
                      fontFamily: forensicFont,
                      fontSize: 13,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 1.5,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              InkWell(
                onTap: () {
                  setState(() {
                    _isChatMinimized = true;
                  });
                },
                borderRadius: BorderRadius.circular(6),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryCyan.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: AppTheme.primaryCyan.withOpacity(0.4)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.keyboard_double_arrow_left, size: 14, color: AppTheme.primaryCyanLight),
                      SizedBox(width: 4),
                      Text(
                        'Minimize',
                        style: TextStyle(
                          fontFamily: forensicFont,
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
        ),

        // Cyber Teal Linear Question progress bar (Safely Constrained)
        SizedBox(
          width: double.infinity,
          height: 3.0,
          child: LinearProgressIndicator(
            value: (_currentQuestionIndex + 1) / _forensicQuestions.length,
            backgroundColor: const Color(0xFF161E2E),
            color: AppTheme.primaryCyan,
            minHeight: 3.0,
          ),
        ),

        // Message List
        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            itemCount: _messages.length,
            itemBuilder: (context, index) {
              final message = _messages[index];
              return _buildMessageBubble(
                message,
                isLatestWitness: message.id == latestWitnessId,
              );
            },
          ),
        ),

        // Processing indicator
        if (_isProcessing)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
            alignment: Alignment.centerLeft,
            child: const Row(
              children: [
                SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppTheme.primaryCyan,
                  ),
                ),
                SizedBox(width: 8),
                Text(
                  'Adjusting 3D face structure...',
                  style: TextStyle(
                    fontFamily: forensicFont,
                    fontSize: 12,
                    color: AppTheme.primaryCyanLight,
                  ),
                ),
              ],
            ),
          ),

        // Bottom Input Area (Cyber Teal Theme)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: const Color(0xFF0E131C),
            borderRadius: const BorderRadius.vertical(bottom: Radius.circular(15)),
            border: Border(
              top: BorderSide(color: AppTheme.primaryCyan.withOpacity(0.35)),
            ),
          ),
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.mic_none_rounded, color: AppTheme.primaryCyanLight),
                onPressed: _onMicrophonePressed,
              ),
              Expanded(
                child: TextField(
                  controller: _textController,
                  focusNode: _focusNode,
                  style: const TextStyle(
                    fontFamily: forensicFont,
                    fontSize: 14.5,
                    color: Colors.white,
                  ),
                  cursorColor: AppTheme.primaryCyan,
                  decoration: InputDecoration(
                    hintText: _isEditingLatest
                        ? 'Edit answer...'
                        : 'Describe (e.g., face little big, oval, okay)...',
                    hintStyle: const TextStyle(
                      fontFamily: forensicFont,
                      color: Colors.white38,
                    ),
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    filled: true,
                    fillColor: const Color(0xFF141C2A),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(20),
                      borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(20),
                      borderSide: BorderSide(color: Colors.white.withOpacity(0.1)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(20),
                      borderSide: const BorderSide(color: AppTheme.primaryCyan, width: 1.5),
                    ),
                  ),
                  onSubmitted: (_) => _sendMessage(),
                ),
              ),
              const SizedBox(width: 8),
              Material(
                color: Colors.transparent,
                child: InkWell(
                  borderRadius: BorderRadius.circular(20),
                  onTap: _sendMessage,
                  child: Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppTheme.primaryCyan,
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.primaryCyan.withOpacity(0.6),
                          blurRadius: 10,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                    child: const Icon(Icons.send_rounded, color: Colors.white, size: 18),
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMessageBubble(ChatMessage message, {required bool isLatestWitness}) {
    final isWitness = message.isWitness;
    final isSystem = message.isSystem;

    if (isSystem) {
      return Center(
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 8),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: AppTheme.primaryCyan.withOpacity(0.12),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: AppTheme.primaryCyan.withOpacity(0.4)),
          ),
          child: Text(
            message.text,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontFamily: forensicFont,
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: AppTheme.primaryCyanLight,
            ),
          ),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        mainAxisAlignment:
            isWitness ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isWitness) ...[
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: const Color(0xFF141C2A),
                shape: BoxShape.circle,
                border: Border.all(color: AppTheme.primaryCyan.withOpacity(0.6)),
              ),
              child: const Icon(
                Icons.support_agent_rounded,
                size: 16,
                color: AppTheme.primaryCyanLight,
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Column(
              crossAxisAlignment:
                  isWitness ? CrossAxisAlignment.end : CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: isWitness ? const Color(0xFF15202E) : const Color(0xFF101622),
                    borderRadius: BorderRadius.circular(12),
                    border: Border(
                      left: isWitness
                          ? BorderSide.none
                          : const BorderSide(color: AppTheme.primaryCyan, width: 3.5),
                      top: BorderSide(
                        color: isWitness
                            ? AppTheme.primaryCyan.withOpacity(0.35)
                            : Colors.white.withOpacity(0.08),
                      ),
                      right: BorderSide(
                        color: isWitness
                            ? AppTheme.primaryCyan.withOpacity(0.35)
                            : Colors.white.withOpacity(0.08),
                      ),
                      bottom: BorderSide(
                        color: isWitness
                            ? AppTheme.primaryCyan.withOpacity(0.35)
                            : Colors.white.withOpacity(0.08),
                      ),
                    ),
                  ),
                  child: Text(
                    message.text,
                    style: TextStyle(
                      fontFamily: forensicFont,
                      fontSize: 14,
                      color: isWitness ? Colors.white : AppTheme.textPrimary,
                      height: 1.35,
                    ),
                  ),
                ),
                if (isWitness && isLatestWitness)
                  Padding(
                    padding: const EdgeInsets.only(top: 2, right: 4),
                    child: InkWell(
                      onTap: () => _startEditingLatestAnswer(message),
                      child: const Text(
                        'Edit answer',
                        style: TextStyle(
                          fontFamily: forensicFont,
                          fontSize: 11,
                          color: AppTheme.primaryCyanLight,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          if (isWitness) ...[
            const SizedBox(width: 8),
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: const Color(0xFF141C2A),
                shape: BoxShape.circle,
                border: Border.all(color: AppTheme.primaryCyan.withOpacity(0.4)),
              ),
              child: const Icon(
                Icons.person_outline_rounded,
                size: 16,
                color: Colors.white70,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
