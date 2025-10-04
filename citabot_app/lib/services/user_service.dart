import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'dart:convert';
import '../config.dart';

class UserService {
  // Singleton pattern
  static final UserService _instance = UserService._internal();
  factory UserService() => _instance;
  UserService._internal();

  // Firebase instances
  static final FirebaseMessaging _firebaseMessaging =
      FirebaseMessaging.instance;

  // State variables
  static String? _currentToken;
  static String? _userId;

  // Storage keys
  static const String _userIdKey = 'user_id';
  static const String _lastUsagePingKey = 'last_usage_ping';
  static const String _localUserIdKey = 'local_user_id';

  /// Initialize complete user service (notifications + tracking)
  static Future<void> initialize() async {
    debugPrint('🚀 Initializing UserService...');

    // 1. Get or create user ID
    await _initializeUserId();

    // 2. Initialize notifications
    await _initializeNotifications();

    // Installation/usage tracking removed from project.

    debugPrint('✅ UserService initialized successfully');
  }

  /// Initialize user ID (Firebase Auth or local fallback)
  static Future<void> _initializeUserId() async {
    try {
      final prefs = await SharedPreferences.getInstance();

      // Check if we already have a stored user ID
      _userId = prefs.getString(_userIdKey);

      if (_userId == null) {
        // Create new user ID
        _userId = await _createUserId();
        if (_userId != null) {
          await prefs.setString(_userIdKey, _userId!);
          debugPrint('👤 New user ID created: $_userId');
          // If we already have an FCM token registered, re-register it with the backend
          // so the backend can associate the token with this newly created user_id.
          try {
            if (_currentToken != null) {
              List<String> favoritos = prefs.getStringList('favoritos') ?? [];
              await _registerTokenWithBackend(
                _currentToken!,
                favoritos: favoritos,
              );
              debugPrint('🔁 Re-registered existing token with new user_id');
            }
          } catch (e) {
            debugPrint(
              '⚠️ Error re-registering token after user id creation: $e',
            );
          }
        }
      } else {
        debugPrint('👤 Existing user ID loaded: $_userId');
      }
    } catch (e) {
      debugPrint('❌ Error initializing user ID: $e');
    }
  }

  /// Create user ID using Firebase Auth or local fallback
  static Future<String?> _createUserId() async {
    try {
      final auth = FirebaseAuth.instance;
      User? currentUser = auth.currentUser;

      if (currentUser == null) {
        try {
          // Try Firebase anonymous auth
          debugPrint('🔐 Creating Firebase anonymous user...');
          final userCredential = await auth.signInAnonymously();
          currentUser = userCredential.user;
        } catch (e) {
          debugPrint('⚠️ Firebase Auth failed: $e');
          debugPrint('🔄 Falling back to local UUID...');

          // Fallback to local UUID
          final prefs = await SharedPreferences.getInstance();
          String? localUserId = prefs.getString(_localUserIdKey);

          if (localUserId == null) {
            final now = DateTime.now().millisecondsSinceEpoch;
            final random = (DateTime.now().microsecondsSinceEpoch % 10000);
            localUserId = 'local_${now}_$random';
            await prefs.setString(_localUserIdKey, localUserId);
          }

          return localUserId;
        }
      }

      return currentUser?.uid;
    } catch (e) {
      debugPrint('❌ Error creating user ID: $e');
      return null;
    }
  }

  /// Initialize Firebase Cloud Messaging
  static Future<void> _initializeNotifications() async {
    if (!Config.enableNotifications) {
      debugPrint('🔕 Notifications disabled in config');
      return;
    }

    try {
      // Request permissions
      NotificationSettings settings = await _firebaseMessaging
          .requestPermission(
            alert: true,
            announcement: false,
            badge: true,
            carPlay: false,
            criticalAlert: false,
            provisional: false,
            sound: true,
          );

      if (settings.authorizationStatus == AuthorizationStatus.authorized) {
        debugPrint('🔔 Notification permissions granted');

        // Get and register FCM token
        await _getAndRegisterToken();

        // Setup message handlers
        _setupMessageHandlers();
      } else {
        debugPrint('❌ Notification permissions denied');
      }
    } catch (e) {
      debugPrint('❌ Error initializing notifications: $e');
    }
  }

  /// Get FCM token and register with backend
  static Future<void> _getAndRegisterToken() async {
    try {
      String? token = await _firebaseMessaging.getToken();
      if (token != null && token != _currentToken) {
        _currentToken = token;

        // Get current favorites
        final prefs = await SharedPreferences.getInstance();
        List<String> favoritos = prefs.getStringList('favoritos') ?? [];

        // Register with backend
        await _registerTokenWithBackend(token, favoritos: favoritos);

        debugPrint('🎯 FCM token registered: ${token.substring(0, 20)}...');
      }
    } catch (e) {
      debugPrint('❌ Error getting FCM token: $e');
    }
  }

  /// Register FCM token with backend
  static Future<void> _registerTokenWithBackend(
    String token, {
    List<String>? favoritos,
  }) async {
    const int maxRetries = 3;
    int attempt = 0;
    final body = {
      'token': token,
      if (_userId != null) 'user_id': _userId,
      if (favoritos != null) 'favoritos': favoritos,
    };

    while (attempt < maxRetries) {
      attempt++;
      try {
        final response = await http.post(
          Uri.parse(Config.registerTokenUrl),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        );

        if (response.statusCode == 200) {
          try {
            final data = jsonDecode(response.body);
            debugPrint(
              '✅ Token registered. Devices: ${data['registered_devices']}',
            );
          } catch (e) {
            debugPrint(
              '✅ Token registered but failed to parse response body: $e',
            );
          }
          return;
        } else {
          // Log response body to help diagnose 5xx/502 responses from backend
          String respBody = response.body;
          // Truncate HTML responses to avoid spam in logs
          if (respBody.contains('<!DOCTYPE html>')) {
            respBody = 'HTML Error Page (${respBody.length} chars)';
          } else if (respBody.length > 200) {
            respBody = '${respBody.substring(0, 200)}...';
          }

          debugPrint(
            '❌ Error registering token (status ${response.statusCode}): $respBody',
          );

          // Retry on server errors (5xx)
          if (response.statusCode >= 500 && attempt < maxRetries) {
            final backoff = Duration(milliseconds: 1000 * attempt);
            debugPrint(
              '🔄 Retrying in ${backoff.inSeconds}s... (attempt $attempt/$maxRetries)',
            );
            await Future.delayed(backoff);
            continue;
          }

          // For non-5xx errors, don't retry
          debugPrint(
            '⚠️ Giving up token registration after ${response.statusCode} error',
          );
          return;
        }
      } catch (e) {
        debugPrint('❌ Error sending token to backend (attempt $attempt): $e');
        if (attempt < maxRetries) {
          await Future.delayed(Duration(milliseconds: 500 * attempt));
          continue;
        }
        return;
      }
    }
  }

  /// Setup FCM message handlers
  static void _setupMessageHandlers() {
    // Handle messages when app is in foreground
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint(
        '📨 Message received in foreground: ${message.notification?.title}',
      );
      _showInAppNotification(message);
    });

    // Handle notification taps when app is in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('👆 Notification tapped: ${message.notification?.title}');
      _handleNotificationTap(message);
    });

    // Handle notifications when app is terminated
    FirebaseMessaging.instance.getInitialMessage().then((
      RemoteMessage? message,
    ) {
      if (message != null) {
        debugPrint(
          '🚀 App opened from notification: ${message.notification?.title}',
        );
        _handleNotificationTap(message);
      }
    });
  }

  /// Show in-app notification
  static void _showInAppNotification(RemoteMessage message) {
    // Show local notification even when app is in foreground
    _showLocalNotificationFromService(message);
    debugPrint('📱 In-app notification: ${message.notification?.body}');
  }

  /// Show local notification from service
  static Future<void> _showLocalNotificationFromService(
    RemoteMessage message,
  ) async {
    try {
      // Import the local notifications plugin
      final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
          FlutterLocalNotificationsPlugin();

      const AndroidNotificationDetails androidPlatformChannelSpecifics =
          AndroidNotificationDetails(
            'citabot_channel',
            'Citabot Notifications',
            channelDescription: 'Notificaciones de citas ITV disponibles',
            importance: Importance.max,
            priority: Priority.high,
            showWhen: true,
            icon: '@mipmap/ic_launcher',
          );

      const NotificationDetails platformChannelSpecifics = NotificationDetails(
        android: androidPlatformChannelSpecifics,
      );

      await flutterLocalNotificationsPlugin.show(
        message.hashCode,
        message.notification?.title ?? 'Nueva cita disponible',
        message.notification?.body ?? 'Hay una nueva cita ITV disponible',
        platformChannelSpecifics,
      );
    } catch (e) {
      debugPrint('Error showing local notification: $e');
    }
  }

  /// Handle notification tap
  static void _handleNotificationTap(RemoteMessage message) {
    final data = message.data;
    if (data['type'] == 'new_appointment') {
      debugPrint(
        '🎯 New appointment: ${data['estacion']} - ${data['fecha']} ${data['hora']}',
      );
      // Could navigate to specific screen here
    }
  }

  // Installation/usage tracking functions removed.

  /// Update user favorites
  static Future<void> updateFavorites(List<String> favoritos) async {
    if (_currentToken == null) {
      debugPrint('❌ No FCM token available to update favorites');
      return;
    }

    try {
      final response = await http.post(
        Uri.parse('${Config.baseUrl}/update-favorites'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'token': _currentToken!, 'favoritos': favoritos}),
      );

      if (response.statusCode == 200) {
        debugPrint('✅ Favorites updated successfully in backend');
      } else {
        debugPrint('❌ Error updating favorites: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('❌ Error sending favorites to backend: $e');
    }
  }

  /// Refresh FCM token
  static Future<void> refreshToken() async {
    await _getAndRegisterToken();
  }

  /// Get current user ID
  static String? getUserId() => _userId;

  /// Get current FCM token
  static String? getCurrentToken() => _currentToken;

  /// Reset all user data (for testing)
  static Future<void> resetUserData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_userIdKey);
      await prefs.remove(_lastUsagePingKey);
      await prefs.remove(_localUserIdKey);

      // Sign out from Firebase
      try {
        await FirebaseAuth.instance.signOut();
      } catch (e) {
        debugPrint('⚠️ Error signing out: $e');
      }

      _userId = null;
      _currentToken = null;

      debugPrint('🔄 User data reset successfully');
    } catch (e) {
      debugPrint('❌ Error resetting user data: $e');
    }
  }

  /// Unsubscribe from notifications: unregister token on backend and delete local token
  static Future<bool> unsubscribeFromNotifications() async {
    if (_currentToken == null) {
      debugPrint('⚠️ No token to unsubscribe');
      return false;
    }

    try {
      final url = Uri.parse('${Config.baseUrl}/unregister-token');
      final response = await http.delete(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'token': _currentToken}),
      );

      if (response.statusCode == 200) {
        debugPrint('🗑️ Token unregistered on backend');

        // Delete token on device
        try {
          await FirebaseMessaging.instance.deleteToken();
          debugPrint('🧹 Local FCM token deleted');
        } catch (e) {
          debugPrint('⚠️ Error deleting local FCM token: $e');
        }

        // Clear stored token in memory; keep user preferences (favoritos) intact
        _currentToken = null;

        return true;
      } else {
        debugPrint(
          '❌ Backend responded with ${response.statusCode} when unregistering',
        );
        return false;
      }
    } catch (e) {
      debugPrint('❌ Error unregistering token: $e');
      return false;
    }
  }
}
