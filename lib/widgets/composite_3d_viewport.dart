import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../models/forensic_asset.dart';
import '../services/api_service.dart';
import '../services/platform_bridge.dart';
import '../theme/app_theme.dart';

class Composite3DViewport extends StatefulWidget {
  final CompositeParams params;
  final Function(CompositeParams)? onParamsChanged;
  final VoidCallback? onConfirmPressed;
  final VoidCallback? onGenerateSketchPressed;

  const Composite3DViewport({
    super.key,
    required this.params,
    this.onParamsChanged,
    this.onConfirmPressed,
    this.onGenerateSketchPressed,
  });

  @override
  State<Composite3DViewport> createState() => _Composite3DViewportState();
}

class _Composite3DViewportState extends State<Composite3DViewport> {
  String _selectedCamera = 'front';
  String _viewId = 'threejs-viewer-iframe';

  String _selectedCategory = 'hair';

  // Active slot tracking: slot -> assetId
  final Map<String, String> _activeSlotAssets = {
    'hair': 'none',
    'eyebrows': 'none',
    'eyelashes': 'none',
    'glasses': 'none',
    'moustache': 'none',
    'beard': 'none',
    'nose': 'none',
    'ears': 'none',
    'eyes': 'eyes_hazel',
    'skin': 'fair',
  };

  bool _isGalleryCollapsed = false;

  // Fine-tuning offsets per slot
  final Map<String, Map<String, double>> _slotOffsets = {
    'hair': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'eyebrows': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'eyelashes': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'eyes': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'glasses': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'moustache': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'beard': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'nose': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'ears': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'hats': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
    'outfits': {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0},
  };

  final List<Map<String, dynamic>> _categories = [
    {'slot': 'hair', 'title': 'Hair', 'icon': Icons.face_retouching_natural},
    {'slot': 'eyebrows', 'title': 'Eyebrows', 'icon': Icons.remove_red_eye_outlined},
    {'slot': 'eyelashes', 'title': 'Eyelashes', 'icon': Icons.visibility},
    {'slot': 'eyes', 'title': 'Eyes', 'icon': Icons.remove_red_eye},
    {'slot': 'glasses', 'title': 'Glasses', 'icon': Icons.visibility_outlined},
    {'slot': 'hats', 'title': 'Hats', 'icon': Icons.military_tech},
    {'slot': 'outfits', 'title': 'Outfits', 'icon': Icons.checkroom},
    {'slot': 'moustache', 'title': 'Moustache', 'icon': Icons.horizontal_rule},
    {'slot': 'beard', 'title': 'Beard', 'icon': Icons.man},
    {'slot': 'nose', 'title': 'Nose', 'icon': Icons.change_history},
    {'slot': 'ears', 'title': 'Ears', 'icon': Icons.hearing},
    {'slot': 'skin', 'title': 'Skin', 'icon': Icons.palette_outlined},
  ];

  @override
  void initState() {
    super.initState();
    if (kIsWeb) {
      _initWebIframe();
    }
  }

  void _initWebIframe() {
    _viewId = 'threejs-viewer-${DateTime.now().millisecondsSinceEpoch}';
    PlatformBridge.initIframe(
      _viewId,
      'viewer3d.html?v=${DateTime.now().millisecondsSinceEpoch}',
      onMessage: (data) {
        if (data['type'] == 'OFFSET_CHANGED') {
          final slot = data['slot'] as String?;
          final y = (data['offsetY'] as num?)?.toDouble();
          final z = (data['offsetZ'] as num?)?.toDouble();
          if (slot != null && y != null && z != null) {
            setState(() {
              _slotOffsets[slot] ??= {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0};
              _slotOffsets[slot]!['offsetY'] = y;
              _slotOffsets[slot]!['offsetZ'] = z;
            });
          }
        }
      },
    );
  }

  @override
  void didUpdateWidget(covariant Composite3DViewport oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.params.model != widget.params.model) {
      _sendModelUpdate();
    }
  }

  void _sendModelUpdate() {
    PlatformBridge.postToIframe({
      'type': 'LOAD_MODEL',
      'model': 'models/${widget.params.model}',
    });
  }

  void _applyAssetToScene(String slot, String assetId) {
    setState(() {
      _activeSlotAssets[slot] = assetId;
    });

    final assetList = _getAssetsForCategory(slot);
    final asset = assetList.firstWhere(
      (a) => a.id == assetId,
      orElse: () => ForensicAsset(slot: slot, id: assetId, name: assetId, description: ''),
    );

    final offsets = _slotOffsets[slot] ?? {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0};
    PlatformBridge.postToIframe({
      'type': 'APPLY_ASSET',
      'slot': slot,
      'assetId': assetId,
      'obj': asset.obj,
      'texture': asset.texture,
      'target': asset.target,
      'offsets': offsets,
    });
  }

  void _removeAssetFromScene(String slot) {
    setState(() {
      _activeSlotAssets[slot] = 'none';
      _slotOffsets[slot] = {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0};
    });

    PlatformBridge.postToIframe({
      'type': 'REMOVE_ASSET',
      'slot': slot,
    });
  }

  void _resetOffset(String slot) {
    setState(() {
      _slotOffsets[slot] = {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0};
    });

    final activeId = _activeSlotAssets[slot] ?? 'none';
    if (activeId != 'none') {
      _applyAssetToScene(slot, activeId);
    }
  }

  void _updateOffset(String slot, String field, double val) {
    setState(() {
      _slotOffsets[slot]![field] = val;
    });

    final activeId = _activeSlotAssets[slot] ?? 'none';
    if (activeId != 'none') {
      _applyAssetToScene(slot, activeId);
    }
  }

  void _setCameraPreset(String preset) {
    setState(() {
      _selectedCamera = preset;
    });
    PlatformBridge.postToIframe({
      'type': 'SET_CAMERA',
      'preset': preset,
    });
  }

  void _setFocus(String focus) {
    final updated = widget.params.copyWith(focus: focus);
    widget.onParamsChanged?.call(updated);
    PlatformBridge.postToIframe({
      'type': 'SET_FOCUS',
      'focus': focus,
    });
  }

  void _switchGenderModel(String modelName) {
    final updated = widget.params.copyWith(
      model: modelName,
      gender: modelName.contains('female') ? 'female' : 'male',
    );
    widget.onParamsChanged?.call(updated);
  }

  List<ForensicAsset> _getAssetsForCategory(String slot) {
    switch (slot) {
      case 'hair':
        return AssetCatalog.hairAssets;
      case 'eyebrows':
        return AssetCatalog.eyebrowAssets;
      case 'eyelashes':
        return AssetCatalog.eyelashAssets;
      case 'eyes':
        return AssetCatalog.eyeAssets;
      case 'glasses':
        return AssetCatalog.glassesAssets;
      case 'hats':
        return AssetCatalog.hatAssets;
      case 'outfits':
        return AssetCatalog.outfitAssets;
      case 'moustache':
        return AssetCatalog.moustacheAssets;
      case 'beard':
        return AssetCatalog.beardAssets;
      case 'nose':
        return AssetCatalog.noseAssets;
      case 'ears':
        return AssetCatalog.earAssets;
      case 'skin':
        return AssetCatalog.skinAssets;
      default:
        return [];
    }
  }

  @override
  Widget build(BuildContext context) {
    final isConfirmed = widget.params.isConfirmed;
    final isFaceFocus = widget.params.focus == 'face';
    final isMale = widget.params.model.contains('male') && !widget.params.model.contains('female');

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surface,
        border: Border.all(color: AppTheme.border),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Viewport Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: AppTheme.surfaceLight,
              borderRadius: BorderRadius.vertical(top: Radius.circular(15)),
              border: Border(bottom: BorderSide(color: AppTheme.border)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.psychology_rounded,
                        color: AppTheme.primaryCyan, size: 22),
                    const SizedBox(width: 8),
                    const Text(
                      '3D Facial Composite Studio',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Model Toggle
                    Container(
                      padding: const EdgeInsets.all(2),
                      decoration: BoxDecoration(
                        color: AppTheme.surface,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: AppTheme.border),
                      ),
                      child: Row(
                        children: [
                          _buildModelToggleBtn('Male', isMale, () => _switchGenderModel('male.glb')),
                          _buildModelToggleBtn('Female', !isMale, () => _switchGenderModel('female.glb')),
                        ],
                      ),
                    ),
                  ],
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: isConfirmed
                        ? AppTheme.statusActive.withOpacity(0.15)
                        : AppTheme.primaryCyan.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: isConfirmed
                          ? AppTheme.statusActive
                          : AppTheme.primaryCyanLight.withOpacity(0.7),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        isConfirmed ? Icons.check_circle : Icons.auto_awesome,
                        size: 13,
                        color: isConfirmed
                            ? AppTheme.statusActive
                            : AppTheme.primaryCyanLight,
                      ),
                      const SizedBox(width: 5),
                      Text(
                        isConfirmed ? 'COMPOSITE CONFIRMED' : 'AUTO-FIT ACTIVE',
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.bold,
                          color: isConfirmed
                              ? AppTheme.statusActive
                              : AppTheme.primaryCyanLight,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // 3D Canvas / Viewport Area (Dynamically expands when gallery is collapsed!)
          Expanded(
            flex: _isGalleryCollapsed ? 14 : 7,
            child: Stack(
              children: [
                PlatformBridge.buildView(
                  _viewId,
                  mobileFallback: _buildMobileFallback(),
                ),

                // Camera Angle Controls (Bottom-left)
                Positioned(
                  bottom: 12,
                  left: 12,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.surface.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.border),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildPresetBtn('Front', 'front'),
                        const SizedBox(width: 4),
                        _buildPresetBtn('45°', 'angle'),
                        const SizedBox(width: 4),
                        _buildPresetBtn('Profile', 'profile'),
                      ],
                    ),
                  ),
                ),

                // Focus Camera Toggle (Top-left)
                Positioned(
                  top: 12,
                  left: 12,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppTheme.surface.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppTheme.border),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildFocusBtn('🔍 Face Close-up', 'face', isFaceFocus),
                        const SizedBox(width: 4),
                        _buildFocusBtn('🧍 Full Body', 'body', !isFaceFocus),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Categorized Asset Gallery & Attachment Controls
          _isGalleryCollapsed
              ? Container(
                  height: 46,
                  decoration: const BoxDecoration(
                    color: AppTheme.surface,
                    border: Border(top: BorderSide(color: AppTheme.border)),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: ListView.builder(
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          itemCount: _categories.length,
                          itemBuilder: (context, idx) {
                            final cat = _categories[idx];
                            final slot = cat['slot'] as String;
                            final isSelected = slot == _selectedCategory;
                            return InkWell(
                              onTap: () {
                                setState(() {
                                  _selectedCategory = slot;
                                  _isGalleryCollapsed = false;
                                });
                              },
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 12),
                                alignment: Alignment.center,
                                child: Text(
                                  cat['title'] as String,
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                                    color: isSelected ? AppTheme.primaryCyanLight : AppTheme.textSecondary,
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                      InkWell(
                        onTap: () => setState(() => _isGalleryCollapsed = false),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          child: Row(
                            children: const [
                              Icon(Icons.keyboard_arrow_up, size: 16, color: AppTheme.primaryCyanLight),
                              SizedBox(width: 4),
                              Text('Show Assets', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.primaryCyanLight)),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                )
              : Expanded(
                  flex: 5,
                  child: Container(
                    decoration: const BoxDecoration(
                      color: AppTheme.surfaceLight,
                      border: Border(top: BorderSide(color: AppTheme.border)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Horizontal Category Selector Tabs with Collapse Button
                        Container(
                          height: 44,
                          decoration: const BoxDecoration(
                            color: AppTheme.surface,
                            border: Border(bottom: BorderSide(color: AppTheme.border)),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: ListView.builder(
                                  scrollDirection: Axis.horizontal,
                                  padding: const EdgeInsets.symmetric(horizontal: 8),
                                  itemCount: _categories.length,
                                  itemBuilder: (context, idx) {
                                    final cat = _categories[idx];
                                    final slot = cat['slot'] as String;
                                    final isSelected = slot == _selectedCategory;
                                    final hasActiveAsset = _activeSlotAssets[slot] != 'none';

                                    return InkWell(
                                      onTap: () {
                                        setState(() {
                                          _selectedCategory = slot;
                                        });
                                      },
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 12),
                                        alignment: Alignment.center,
                                        decoration: BoxDecoration(
                                          border: Border(
                                            bottom: BorderSide(
                                              color: isSelected
                                                  ? AppTheme.primaryCyan
                                                  : Colors.transparent,
                                              width: 2.5,
                                            ),
                                          ),
                                        ),
                                        child: Row(
                                          children: [
                                            Text(
                                              cat['title'] as String,
                                              style: TextStyle(
                                                fontSize: 12,
                                                fontWeight: isSelected
                                                    ? FontWeight.bold
                                                    : FontWeight.w500,
                                                color: isSelected
                                                    ? AppTheme.primaryCyanLight
                                                    : AppTheme.textSecondary,
                                              ),
                                            ),
                                            if (hasActiveAsset && slot != 'skin') ...[
                                              const SizedBox(width: 5),
                                              Container(
                                                width: 6,
                                                height: 6,
                                                decoration: const BoxDecoration(
                                                  color: AppTheme.statusActive,
                                                  shape: BoxShape.circle,
                                                ),
                                              ),
                                            ],
                                          ],
                                        ),
                                      ),
                                    );
                                  },
                                ),
                              ),
                              InkWell(
                                onTap: () => setState(() => _isGalleryCollapsed = true),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10),
                                  child: Row(
                                    children: const [
                                      Icon(Icons.keyboard_arrow_down, size: 16, color: AppTheme.textSecondary),
                                      SizedBox(width: 4),
                                      Text('Hide', style: TextStyle(fontSize: 10, color: AppTheme.textSecondary)),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),

                        // Asset Cards & Fine-Tuning Drawer
                        Expanded(
                          child: SingleChildScrollView(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _buildAssetCardsGrid(_selectedCategory),
                                if (_selectedCategory != 'skin' && _activeSlotAssets[_selectedCategory] != 'none') ...[
                                  const Divider(color: AppTheme.border, height: 24),
                                  _buildFineTuneSliders(_selectedCategory),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

          // Action Confirmation Footer
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: const BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(15)),
              border: Border(top: BorderSide(color: AppTheme.border)),
            ),
            child: Row(
              children: [
                Expanded(
                  flex: 3,
                  child: ElevatedButton.icon(
                    onPressed: widget.onConfirmPressed,
                    icon: const Icon(Icons.check_circle_rounded, size: 18),
                    label: Text(
                      isConfirmed
                          ? 'Composite Confirmed ✓'
                          : 'Confirm Current Feature',
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isConfirmed
                          ? AppTheme.statusActive
                          : AppTheme.primaryCyan,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  flex: 2,
                  child: OutlinedButton.icon(
                    onPressed: widget.onGenerateSketchPressed,
                    icon: const Icon(Icons.art_track_rounded, size: 16),
                    label: const Text('2D Sketch / Photo'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
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

  Widget _buildAssetCardsGrid(String slot) {
    final assets = _getAssetsForCategory(slot);
    final activeId = _activeSlotAssets[slot] ?? 'none';

    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        // "None / Remove" Card
        if (slot != 'skin')
          _buildNoneCard(slot, activeId == 'none'),

        // Asset Cards
        ...assets.map((asset) {
          final isSelected = activeId == asset.id;
          return _buildAssetCard(slot, asset, isSelected);
        }),
      ],
    );
  }

  Widget _buildNoneCard(String slot, bool isSelected) {
    return InkWell(
      onTap: () => _removeAssetFromScene(slot),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 140,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryCyan.withOpacity(0.18) : AppTheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? AppTheme.primaryCyanLight : AppTheme.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.block_rounded,
                  size: 16,
                  color: isSelected ? AppTheme.primaryCyanLight : AppTheme.textMuted,
                ),
                const SizedBox(width: 6),
                Text(
                  'None',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
                    color: isSelected ? Colors.white : AppTheme.textPrimary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            const Text(
              'Remove active asset',
              style: TextStyle(fontSize: 10, color: AppTheme.textMuted),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAssetCard(String slot, ForensicAsset asset, bool isSelected) {
    return InkWell(
      onTap: () => _applyAssetToScene(slot, asset.id),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 165,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryCyan.withOpacity(0.15) : AppTheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? AppTheme.primaryCyanLight : AppTheme.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (asset.thumb != null) ...[
              ClipRRect(
                borderRadius: BorderRadius.circular(6),
                child: Container(
                  height: 72,
                  width: double.infinity,
                  color: const Color(0xFF101216),
                  child: Image.network(
                    asset.thumb!,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) => const Center(
                      child: Icon(Icons.broken_image, size: 20, color: AppTheme.textMuted),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 6),
            ],
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    asset.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
                      color: isSelected ? Colors.white : AppTheme.textPrimary,
                    ),
                  ),
                ),
                if (isSelected)
                  const Icon(Icons.check_circle, size: 14, color: AppTheme.statusActive),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              asset.description,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 10, color: AppTheme.textMuted, height: 1.2),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    asset.license,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 9, color: AppTheme.textSecondary),
                  ),
                ),
                const SizedBox(width: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: isSelected ? AppTheme.statusActive : AppTheme.primaryCyan,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    isSelected ? 'Active' : 'Apply',
                    style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFineTuneSliders(String slot) {
    final offsets = _slotOffsets[slot] ?? {'offsetY': 0.0, 'offsetZ': 0.0, 'scale': 1.0};
    final offsetY = offsets['offsetY'] ?? 0.0;
    final offsetZ = offsets['offsetZ'] ?? 0.0;
    final scale = offsets['scale'] ?? 1.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'FINE-TUNE ATTACHMENT (${slot.toUpperCase()})',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                letterSpacing: 1,
                color: AppTheme.primaryCyanLight,
              ),
            ),
            InkWell(
              onTap: () => _resetOffset(slot),
              child: const Text(
                'Reset Offset',
                style: TextStyle(fontSize: 11, color: AppTheme.textSecondary, decoration: TextDecoration.underline),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),

        // Vertical Offset Slider
        _buildOffsetSlider(
          label: 'Vertical Alignment (Y)',
          value: offsetY,
          min: (slot == 'outfits') ? -0.60 : ((slot == 'hair' || slot == 'hats') ? -0.15 : -0.06),
          max: (slot == 'outfits') ? 0.60 : ((slot == 'hair' || slot == 'hats') ? 0.15 : 0.06),
          format: (v) => '${(v * 100).toStringAsFixed(1)} cm',
          onChanged: (v) => _updateOffset(slot, 'offsetY', v),
        ),

        // Depth Offset Slider
        _buildOffsetSlider(
          label: 'Depth Alignment (Z)',
          value: offsetZ,
          min: (slot == 'outfits') ? -0.30 : ((slot == 'hair' || slot == 'hats') ? -0.15 : -0.06),
          max: (slot == 'outfits') ? 0.30 : ((slot == 'hair' || slot == 'hats') ? 0.15 : 0.06),
          format: (v) => '${(v * 100).toStringAsFixed(1)} cm',
          onChanged: (v) => _updateOffset(slot, 'offsetZ', v),
        ),

        // Scale Slider
        _buildOffsetSlider(
          label: 'Proportional Scale',
          value: scale,
          min: 0.80,
          max: 1.25,
          format: (v) => '${v.toStringAsFixed(2)}x',
          onChanged: (v) => _updateOffset(slot, 'scale', v),
        ),
      ],
    );
  }

  Widget _buildOffsetSlider({
    required String label,
    required double value,
    required double min,
    required double max,
    required String Function(double) format,
    required ValueChanged<double> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3.0),
      child: Row(
        children: [
          SizedBox(
            width: 140,
            child: Text(label, style: const TextStyle(fontSize: 11.5, color: AppTheme.textPrimary)),
          ),
          IconButton(
            icon: const Icon(Icons.remove_circle_outline, size: 16, color: AppTheme.textSecondary),
            onPressed: () => onChanged((value - (max - min) / 20).clamp(min, max)),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
          ),
          Expanded(
            child: SliderTheme(
              data: SliderTheme.of(context).copyWith(
                activeTrackColor: AppTheme.primaryCyan,
                inactiveTrackColor: AppTheme.border,
                thumbColor: AppTheme.primaryCyanLight,
                trackHeight: 3,
                thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 5),
              ),
              child: Slider(
                value: value.clamp(min, max),
                min: min,
                max: max,
                onChanged: onChanged,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.add_circle_outline, size: 16, color: AppTheme.textSecondary),
            onPressed: () => onChanged((value + (max - min) / 20).clamp(min, max)),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
          ),
          SizedBox(
            width: 50,
            child: Text(
              format(value),
              textAlign: TextAlign.end,
              style: const TextStyle(fontSize: 11, fontFamily: 'monospace', fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModelToggleBtn(String label, bool isSelected, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: isSelected ? AppTheme.primaryCyan : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? Colors.white : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildFocusBtn(String label, String focus, bool isSelected) {
    return InkWell(
      onTap: () => _setFocus(focus),
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected
              ? AppTheme.primaryCyan.withOpacity(0.3)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? AppTheme.primaryCyanLight : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildPresetBtn(String label, String preset) {
    final isSelected = _selectedCamera == preset;
    return InkWell(
      onTap: () => _setCameraPreset(preset),
      borderRadius: BorderRadius.circular(4),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected
              ? AppTheme.primaryCyan.withOpacity(0.3)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
            color: isSelected ? AppTheme.primaryCyanLight : AppTheme.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildMobileFallback() {
    return Center(
      child: Container(
        margin: const EdgeInsets.all(24),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surfaceLight,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.primaryCyan.withOpacity(0.4)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.view_in_ar_rounded, size: 48, color: AppTheme.primaryCyanLight),
            const SizedBox(height: 12),
            const Text(
              '3D FORENSIC STUDIO',
              style: TextStyle(
                fontFamily: 'monospace',
                fontWeight: FontWeight.bold,
                color: AppTheme.textPrimary,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Mobile Mode Active // ${widget.params.model.toUpperCase()}',
              style: const TextStyle(
                fontSize: 11,
                color: AppTheme.primaryCyanLight,
                fontFamily: 'monospace',
              ),
            ),
            const SizedBox(height: 10),
            const Text(
              'Adjust biometric features below or use the interview chat to generate 3D forensic composite.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11, color: AppTheme.textSecondary),
            ),
          ],
        ),
      ),
    );
  }
}
