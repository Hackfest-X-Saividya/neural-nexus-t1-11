import 'dart:async';
import 'package:flutter/material.dart';

class PlatformBridge {
  static void initIframe(
    String viewId,
    String src, {
    void Function(Map<String, dynamic> data)? onMessage,
  }) {
    // No-op on mobile / desktop platforms (Android, iOS, Windows)
  }

  static void postToIframe(Map<String, dynamic> message) {
    // No-op on mobile / desktop platforms
  }

  static void broadcastMessage(Map<String, dynamic> message) {
    // No-op on mobile / desktop platforms
  }

  static StreamSubscription? listenWebMessages(
    void Function(Map<String, dynamic> data) onMessage,
  ) {
    return null;
  }

  static void downloadFile(String dataUrl, String filename) {
    // No-op on mobile platforms
  }

  static Widget buildView(
    String viewId, {
    required Widget mobileFallback,
  }) {
    return mobileFallback;
  }

  static final Map<String, String> _memStorage = {};

  static void setStorage(String key, String value) {
    _memStorage[key] = value;
  }

  static String? getStorage(String key) {
    return _memStorage[key];
  }

  static void removeStorage(String key) {
    _memStorage.remove(key);
  }
}

