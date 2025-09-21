import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../config.dart';

class InstallationTracker {
  static const String _hasTrackedKey = 'has_tracked_installation';
  static const String _userIdKey = 'user_id';

  /// Tracks app installation if not already tracked
  static Future<void> trackInstallationIfNeeded() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final hasTracked = prefs.getBool(_hasTrackedKey) ?? false;
      
      if (hasTracked) {
        debugPrint('Installation already tracked, skipping...');
        return;
      }

      // Get or create anonymous user
      final userId = await _getOrCreateAnonymousUser();
      if (userId == null) {
        debugPrint('Failed to get user ID, cannot track installation');
        return;
      }

      // Track installation
      final success = await _sendInstallationData(userId);
      
      if (success) {
        // Mark as tracked
        await prefs.setBool(_hasTrackedKey, true);
        await prefs.setString(_userIdKey, userId);
        debugPrint('✅ Installation tracked successfully for user: $userId');
      } else {
        debugPrint('❌ Failed to track installation');
      }
    } catch (e) {
      debugPrint('Error tracking installation: $e');
    }
  }

  /// Tracks app usage (daily heartbeat)
  static Future<void> trackAppUsage() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final userId = prefs.getString(_userIdKey);
      
      if (userId == null) {
        debugPrint('No user ID found, cannot track usage');
        return;
      }

      await _sendUsageData(userId);
      debugPrint('📊 App usage tracked for user: $userId');
    } catch (e) {
      debugPrint('Error tracking usage: $e');
    }
  }

  /// Gets stored user ID
  static Future<String?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userIdKey);
  }

  /// Creates or gets anonymous Firebase user
  static Future<String?> _getOrCreateAnonymousUser() async {
    try {
      final auth = FirebaseAuth.instance;
      
      // Check if user is already signed in
      User? currentUser = auth.currentUser;
      
      if (currentUser == null) {
        // Try to sign in anonymously with Firebase
        debugPrint('Creating anonymous Firebase user...');
        try {
          final userCredential = await auth.signInAnonymously();
          currentUser = userCredential.user;
        } catch (e) {
          debugPrint('Firebase Auth failed: $e');
          debugPrint('Falling back to local UUID generation...');
          
          // Fallback: Generate local UUID if Firebase Auth is not configured
          final prefs = await SharedPreferences.getInstance();
          String? localUserId = prefs.getString('local_user_id');
          
          if (localUserId == null) {
            // Generate a unique ID based on timestamp and random
            final now = DateTime.now().millisecondsSinceEpoch;
            final random = (DateTime.now().microsecondsSinceEpoch % 10000);
            localUserId = 'local_${now}_$random';
            await prefs.setString('local_user_id', localUserId);
            debugPrint('Generated local user ID: $localUserId');
          } else {
            debugPrint('Using existing local user ID: $localUserId');
          }
          
          return localUserId;
        }
      }
      
      if (currentUser != null) {
        debugPrint('Firebase user ID: ${currentUser.uid}');
        return currentUser.uid;
      }
      
      return null;
    } catch (e) {
      debugPrint('Error creating anonymous user: $e');
      return null;
    }
  }

  /// Sends installation data to backend
  static Future<bool> _sendInstallationData(String userId) async {
    try {
      final url = Uri.parse(Config.trackInstallationUrl);
      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'user_id': userId,
          'platform': 'android',
          'timestamp': DateTime.now().toIso8601String(),
          'app_version': '1.0.7', // You can get this from package_info_plus if needed
          'event_type': 'install',
        }),
      ).timeout(Duration(seconds: 10));

      if (response.statusCode == 200) {
        debugPrint('✅ Installation data sent successfully');
        return true;
      } else {
        debugPrint('❌ Failed to send installation data: ${response.statusCode}');
        debugPrint('Response: ${response.body}');
        return false;
      }
    } catch (e) {
      debugPrint('Error sending installation data: $e');
      return false;
    }
  }

  /// Sends usage data to backend (daily heartbeat)
  static Future<bool> _sendUsageData(String userId) async {
    try {
      final url = Uri.parse(Config.trackUsageUrl);
      final response = await http.post(
        url,
        headers: {
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'user_id': userId,
          'timestamp': DateTime.now().toIso8601String(),
          'event_type': 'usage',
        }),
      ).timeout(Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error sending usage data: $e');
      return false;
    }
  }

  /// Forces re-tracking (useful for testing)
  static Future<void> resetTracking() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_hasTrackedKey);
    await prefs.remove(_userIdKey);
    
    // Sign out from Firebase to create new anonymous user
    try {
      await FirebaseAuth.instance.signOut();
    } catch (e) {
      debugPrint('Error signing out: $e');
    }
    
    debugPrint('🔄 Installation tracking reset');
  }

  /// Gets installation status
  static Future<bool> hasTrackedInstallation() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_hasTrackedKey) ?? false;
  }
}