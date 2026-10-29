import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:ui_web' as ui_web;
import 'package:flutter/material.dart';

class PlatformBridge {
  static html.IFrameElement? _currentIframe;
  static StreamSubscription? _msgSubscription;

  static void initIframe(
    String viewId,
    String src, {
    void Function(Map<String, dynamic> data)? onMessage,
  }) {
    _currentIframe = html.IFrameElement()
      ..src = src
      ..style.border = 'none'
      ..style.width = '100%'
      ..style.height = '100%'
      ..allow = 'autoplay; camera; microphone';

    ui_web.platformViewRegistry.registerViewFactory(
      viewId,
      (int id) => _currentIframe!,
    );

    if (onMessage != null) {
      _msgSubscription?.cancel();
      _msgSubscription = html.window.onMessage.listen((event) {
        final data = event.data;
        if (data is Map) {
          onMessage(Map<String, dynamic>.from(data));
        }
      });
    }
  }

  static void postToIframe(Map<String, dynamic> message) {
    if (_currentIframe != null && _currentIframe!.contentWindow != null) {
      _currentIframe!.contentWindow!.postMessage(message, '*');
    }
  }

  static void broadcastMessage(Map<String, dynamic> message) {
    final iframes = html.document.getElementsByTagName('iframe');
    for (var i = 0; i < iframes.length; i++) {
      final ifr = iframes[i] as html.IFrameElement;
      ifr.contentWindow?.postMessage(message, '*');
    }
  }

  static StreamSubscription? listenWebMessages(
    void Function(Map<String, dynamic> data) onMessage,
  ) {
    return html.window.onMessage.listen((event) {
      final data = event.data;
      if (data is Map) {
        onMessage(Map<String, dynamic>.from(data));
      }
    });
  }

  static void downloadFile(String dataUrl, String filename) {
    try {
      if (dataUrl.startsWith('data:')) {
        final commaIdx = dataUrl.indexOf(',');
        if (commaIdx != -1) {
          final header = dataUrl.substring(0, commaIdx);
          final base64Data = dataUrl.substring(commaIdx + 1);
          final mimeMatch = RegExp(r'data:([^;]+);').firstMatch(header);
          final mimeType = mimeMatch != null ? mimeMatch.group(1)! : 'image/png';

          final bytes = base64Decode(base64Data);
          final blob = html.Blob([bytes], mimeType);
          final blobUrl = html.Url.createObjectUrlFromBlob(blob);

          final anchor = html.AnchorElement(href: blobUrl)
            ..setAttribute('download', filename)
            ..style.display = 'none';
          html.document.body?.children.add(anchor);
          anchor.click();
          anchor.remove();

          Future.delayed(const Duration(seconds: 15), () {
            html.Url.revokeObjectUrl(blobUrl);
          });
          return;
        }
      }
    } catch (e) {
      // Fallback to direct anchor if decoding fails
    }

    final anchor = html.AnchorElement(href: dataUrl)
      ..setAttribute('download', filename)
      ..style.display = 'none';
    html.document.body?.children.add(anchor);
    anchor.click();
    anchor.remove();
  }

  static Widget buildView(
    String viewId, {
    required Widget mobileFallback,
  }) {
    return HtmlElementView(viewType: viewId);
  }
}

