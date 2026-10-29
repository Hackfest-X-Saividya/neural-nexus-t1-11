import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'api_service.dart';
import 'platform_bridge.dart';

class CaseRecord {
  final String caseId;
  String title;
  String crimeType;
  String investigator;
  String witnessName;
  String status;
  String notes;
  DateTime createdAt;
  DateTime updatedAt;
  String? latestSketchDataUrl;
  String? latestColoredDataUrl;
  CompositeParams? params;

  CaseRecord({
    required this.caseId,
    this.title = 'Suspect Composite Reconstruction',
    this.crimeType = 'Armed Robbery / Identification',
    this.investigator = 'Detective Unit // Cyber Division',
    this.witnessName = 'Witness #1',
    this.status = 'ACTIVE',
    this.notes = '',
    DateTime? createdAt,
    DateTime? updatedAt,
    this.latestSketchDataUrl,
    this.latestColoredDataUrl,
    this.params,
  })  : createdAt = createdAt ?? DateTime.now(),
        updatedAt = updatedAt ?? DateTime.now();

  Map<String, dynamic> toJson() => {
        'case_id': caseId,
        'title': title,
        'crime_type': crimeType,
        'investigator': investigator,
        'witness_name': witnessName,
        'status': status,
        'notes': notes,
        'created_at': createdAt.toIso8601String(),
        'updated_at': updatedAt.toIso8601String(),
        'latest_sketch': latestSketchDataUrl,
        'latest_colored': latestColoredDataUrl,
        'params': params?.toJson(),
      };

  factory CaseRecord.fromJson(Map<String, dynamic> json) {
    CompositeParams? compParams;
    if (json['params'] != null) {
      try {
        final p = json['params'] as Map<String, dynamic>;
        compParams = CompositeParams(
          model: p['model'] ?? 'male.glb',
          scaleX: (p['scale_x'] as num?)?.toDouble() ?? 1.0,
          scaleY: (p['scale_y'] as num?)?.toDouble() ?? 1.0,
          scaleZ: (p['scale_z'] as num?)?.toDouble() ?? 1.0,
          gender: p['gender'] ?? 'male',
          focus: p['focus'] ?? 'face',
          beard: p['beard'] ?? 'none',
          hair: p['hair'] ?? 'none',
          glasses: p['glasses'] ?? 'none',
          isConfirmed: p['is_confirmed'] ?? false,
          activeFeature: p['active_feature'] ?? 'Face & Jaw',
        );
      } catch (_) {}
    }

    return CaseRecord(
      caseId: json['case_id'] ?? 'CASE-2026-X891',
      title: json['title'] ?? 'Suspect Composite Reconstruction',
      crimeType: json['crime_type'] ?? 'Armed Robbery / Identification',
      investigator: json['investigator'] ?? 'Detective Unit // Cyber Division',
      witnessName: json['witness_name'] ?? 'Witness #1',
      status: json['status'] ?? 'ACTIVE',
      notes: json['notes'] ?? '',
      createdAt: json['created_at'] != null ? DateTime.tryParse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.tryParse(json['updated_at']) : null,
      latestSketchDataUrl: json['latest_sketch'],
      latestColoredDataUrl: json['latest_colored'],
      params: compParams,
    );
  }
}

class ForensicDatabase {
  static const String _storageKey = 'neuracrime_forensic_cases_v1';
  static final Map<String, CaseRecord> _memoryCache = {};
  static bool _isLoaded = false;

  /// Loads cases from persistent storage and seeds initial data if empty
  static void _ensureLoaded() {
    if (_isLoaded) return;
    _isLoaded = true;

    try {
      final raw = PlatformBridge.getStorage(_storageKey);
      if (raw != null && raw.isNotEmpty) {
        final List<dynamic> list = jsonDecode(raw);
        for (var item in list) {
          if (item is Map) {
            final rec = CaseRecord.fromJson(Map<String, dynamic>.from(item));
            _memoryCache[rec.caseId] = rec;
          }
        }
      }
    } catch (e) {
      debugPrint('Notice loading database from local storage: $e');
    }

    // Seed baseline forensic case if none exists
    if (_memoryCache.isEmpty) {
      final baseline = CaseRecord(
        caseId: 'CASE-2026-X891',
        title: 'Metro Bank Armed Sighting',
        crimeType: 'Armed Robbery / Facial Identification',
        investigator: 'Detective Unit // Cyber Division',
        witnessName: 'Sarah M.',
        status: 'ACTIVE',
        notes: 'Suspect observed wearing rectangular forensic glasses with stubble beard.',
      );
      _memoryCache[baseline.caseId] = baseline;
      _saveToPersistentStorage();
    }
  }

  static void _saveToPersistentStorage() {
    try {
      final list = _memoryCache.values.map((c) => c.toJson()).toList();
      PlatformBridge.setStorage(_storageKey, jsonEncode(list));
    } catch (e) {
      debugPrint('Notice saving to persistent storage: $e');
    }
  }

  /// Returns all stored forensic cases sorted by latest updated
  static List<CaseRecord> getAllCases() {
    _ensureLoaded();
    final cases = _memoryCache.values.toList();
    cases.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return cases;
  }

  /// Retrieves a specific case record
  static CaseRecord? getCase(String caseId) {
    _ensureLoaded();
    return _memoryCache[caseId];
  }

  /// Saves or updates a case record
  static void saveCase(CaseRecord record) {
    _ensureLoaded();
    record.updatedAt = DateTime.now();
    _memoryCache[record.caseId] = record;
    _saveToPersistentStorage();
  }

  /// Creates a new case with incremented Case ID
  static CaseRecord createNewCase({
    String? crimeType,
    String? witnessName,
    String? notes,
  }) {
    _ensureLoaded();
    final count = _memoryCache.length + 891;
    final newId = 'CASE-2026-X$count';

    final rec = CaseRecord(
      caseId: newId,
      title: 'Active Investigation $newId',
      crimeType: crimeType ?? 'Felony / Facial Composite',
      investigator: 'Detective Unit // Cyber Division',
      witnessName: witnessName ?? 'Witness #${_memoryCache.length + 1}',
      status: 'ACTIVE',
      notes: notes ?? 'New case file assigned for 3D forensic facial reconstruction.',
    );

    _memoryCache[newId] = rec;
    _saveToPersistentStorage();
    return rec;
  }

  /// Stores 3D composite parameters, 2D sketch, and colored portrait for a case
  static void saveCompositeSnapshot({
    required String caseId,
    required CompositeParams params,
    String? sketchDataUrl,
    String? coloredDataUrl,
    bool markVerified = false,
  }) {
    _ensureLoaded();
    var rec = _memoryCache[caseId];
    if (rec == null) {
      rec = CaseRecord(caseId: caseId);
      _memoryCache[caseId] = rec;
    }

    rec.params = params;
    if (sketchDataUrl != null) rec.latestSketchDataUrl = sketchDataUrl;
    if (coloredDataUrl != null) rec.latestColoredDataUrl = coloredDataUrl;
    if (markVerified) rec.status = 'VERIFIED';
    rec.updatedAt = DateTime.now();

    _saveToPersistentStorage();
  }

  /// Deletes a case from the database
  static bool deleteCase(String caseId) {
    _ensureLoaded();
    final removed = _memoryCache.remove(caseId) != null;
    if (removed) {
      _saveToPersistentStorage();
    }
    return removed;
  }
}
