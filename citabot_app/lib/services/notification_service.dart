import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../config.dart';

class NotificationService {
  static final FirebaseMessaging _firebaseMessaging =
      FirebaseMessaging.instance;
  static String? _currentToken;

  static Future<void> initialize() async {
    // Solicitar permisos
    NotificationSettings settings = await _firebaseMessaging.requestPermission(
      alert: true,
      announcement: false,
      badge: true,
      carPlay: false,
      criticalAlert: false,
      provisional: false,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('Usuario autorizó las notificaciones');

      // Obtener token
      await _getAndRegisterToken();

      // Configurar listeners
      _setupMessageHandlers();
    } else {
      debugPrint('Usuario denegó las notificaciones');
    }
  }

  static Future<void> _getAndRegisterToken() async {
    try {
      String? token = await _firebaseMessaging.getToken();
      if (token != null && token != _currentToken) {
        _currentToken = token;
        await _registerTokenWithBackend(token);
        debugPrint(
          'Token FCM obtenido y registrado: ${token.substring(0, 20)}...',
        );
      }
    } catch (e) {
      debugPrint('Error obteniendo token FCM: $e');
    }
  }

  static Future<void> _registerTokenWithBackend(String token) async {
    try {
      final response = await http.post(
        Uri.parse(Config.registerTokenUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'token': token}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        debugPrint(
          'Token registrado exitosamente. Dispositivos registrados: ${data['registered_devices']}',
        );
      } else {
        debugPrint('Error registrando token: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error enviando token al backend: $e');
    }
  }

  static void _setupMessageHandlers() {
    // Manejar mensajes cuando la app está en primer plano
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint(
        'Mensaje recibido en primer plano: ${message.notification?.title}',
      );
      _showInAppNotification(message);
    });

    // Manejar cuando el usuario toca una notificación
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('Notificación tocada: ${message.notification?.title}');
      _handleNotificationTap(message);
    });

    // Manejar notificaciones cuando la app está cerrada
    FirebaseMessaging.instance.getInitialMessage().then((
      RemoteMessage? message,
    ) {
      if (message != null) {
        debugPrint(
          'App abierta desde notificación: ${message.notification?.title}',
        );
        _handleNotificationTap(message);
      }
    });
  }

  static void _showInAppNotification(RemoteMessage message) {
    // Aquí puedes mostrar una notificación personalizada dentro de la app
    // Por ejemplo, un SnackBar o un Dialog
  }

  static void _handleNotificationTap(RemoteMessage message) {
    // Manejar la navegación cuando el usuario toca una notificación
    final data = message.data;

    if (data['type'] == 'new_appointment') {
      // Navegar a la pantalla de citas o mostrar detalles
      debugPrint(
        'Nueva cita disponible: ${data['estacion']} - ${data['fecha']} ${data['hora']}',
      );
    }
  }

  static Future<void> refreshToken() async {
    await _getAndRegisterToken();
  }

  static String? getCurrentToken() {
    return _currentToken;
  }
}
