import 'dart:async';
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

