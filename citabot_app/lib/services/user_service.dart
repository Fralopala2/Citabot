import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
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

    // 3. Track installation
    await _trackInstallation();

    // 4. Track usage if needed
    await _trackUsageIfNeeded();

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
    try {
      final body = {
        'token': token,
        if (_userId != null) 'user_id': _userId,
        if (favoritos != null) 'favoritos': favoritos,
      };

      final response = await http.post(
        Uri.parse(Config.registerTokenUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        debugPrint(
          '✅ Token registered. Devices: ${data['registered_devices']}',
        );
      } else {
        debugPrint('❌ Error registering token: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('❌ Error sending token to backend: $e');
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
    // Could show SnackBar or custom dialog here
    debugPrint('📱 In-app notification: ${message.notification?.body}');
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

  /// Track app installation
  static Future<void> _trackInstallation() async {
    try {
      if (_userId == null) {
        debugPrint('❌ Cannot track installation: no user ID');
        return;
      }

      // Get app version
      String appVersion = 'unknown';
      try {
        final info = await PackageInfo.fromPlatform();
        appVersion = info.version;
      } catch (e) {
        debugPrint('⚠️ Could not get app version: $e');
      }

      // Send installation data
      final success = await _sendInstallationData(_userId!, appVersion);
      if (success) {
        debugPrint('📊 Installation tracked for user: $_userId');
      } else {
        debugPrint('❌ Failed to track installation');
      }
    } catch (e) {
      debugPrint('❌ Error tracking installation: $e');
    }
  }

  /// Track app usage (daily heartbeat)
  static Future<void> _trackUsageIfNeeded() async {
    try {
      if (_userId == null) return;

      final prefs = await SharedPreferences.getInstance();
      final now = DateTime.now();
      final lastPingStr = prefs.getString(_lastUsagePingKey);

      DateTime? lastPing;
      if (lastPingStr != null) {
        try {
          lastPing = DateTime.parse(lastPingStr);
        } catch (_) {}
      }

      // Only ping if >24h since last ping
      if (lastPing == null || now.difference(lastPing).inHours >= 24) {
        final success = await _sendUsageData(_userId!);
        if (success) {
          await prefs.setString(_lastUsagePingKey, now.toIso8601String());
          debugPrint('💓 Usage heartbeat sent for user: $_userId');
        }
      } else {
        debugPrint('⏳ Usage ping not needed yet (<24h)');
      }
    } catch (e) {
      debugPrint('❌ Error tracking usage: $e');
    }
  }

  /// Send installation data to backend
  static Future<bool> _sendInstallationData(
    String userId,
    String appVersion,
  ) async {
    try {
      final response = await http
          .post(
            Uri.parse(Config.trackInstallationUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'user_id': userId,
              'platform': 'android',
              'timestamp': DateTime.now().toIso8601String(),
              'app_version': appVersion,
              'event_type': 'install',
            }),
          )
          .timeout(Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('❌ Error sending installation data: $e');
      return false;
    }
  }

  /// Send usage data to backend
  static Future<bool> _sendUsageData(String userId) async {
    try {
      final response = await http
          .post(
            Uri.parse(Config.trackUsageUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'user_id': userId,
              'timestamp': DateTime.now().toIso8601String(),
              'event_type': 'usage',
            }),
          )
          .timeout(Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('❌ Error sending usage data: $e');
      return false;
    }
  }

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
}
