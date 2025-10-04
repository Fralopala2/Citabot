import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'horas_disponibles_screen.dart';
import 'config.dart';
import 'favoritos_screen.dart';
import 'categorias_servicio.dart';
// ignore: unused_import
import 'seleccionar_servicio_screen.dart';
import 'services/user_service.dart';

// Plugin de notificaciones locales
final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
    FlutterLocalNotificationsPlugin();

// Handler global para notificaciones en background
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Inicializar Firebase si no está inicializado
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  debugPrint('📨 Background message received: ${message.notification?.title}');
  debugPrint('📨 Background message body: ${message.notification?.body}');
  debugPrint('📨 Background message data: ${message.data}');

  // Mostrar notificación local
  await _showLocalNotification(message);
}

// Función para inicializar notificaciones locales
Future<void> _initializeLocalNotifications() async {
  const AndroidInitializationSettings initializationSettingsAndroid =
      AndroidInitializationSettings('@mipmap/ic_launcher');

  const InitializationSettings initializationSettings = InitializationSettings(
    android: initializationSettingsAndroid,
  );

  await flutterLocalNotificationsPlugin.initialize(
    initializationSettings,
    onDidReceiveNotificationResponse: (NotificationResponse response) {
      debugPrint('Notification tapped: ${response.payload}');
    },
  );
}

// Función para mostrar notificación local
Future<void> _showLocalNotification(RemoteMessage message) async {
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
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // Configurar el handler para notificaciones en background
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  // Inicializar notificaciones locales
  await _initializeLocalNotifications();

  // Start non-blocking initialization tasks after showing UI
  // to avoid delaying app startup. UserService.initialize may do
  // network/auth work and MobileAds initialization may be slow.
  // We still await Firebase because some Firebase APIs may require it.
  runApp(const MyApp());

  // Initialize other services asynchronously without blocking UI
  // Fire-and-forget initializations with error handling
  () async {
    try {
      await UserService.initialize();
    } catch (e) {
      debugPrint('Error initializing UserService in background: $e');
    }
  }();

  () async {
    try {
      await MobileAds.instance.initialize();
    } catch (e) {
      debugPrint('Error initializing MobileAds in background: $e');
    }
  }();
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Citabot App',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.deepPurple,
          iconTheme: IconThemeData(color: Colors.white),
          titleTextStyle: TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w500,
          ),
          toolbarTextStyle: TextStyle(color: Colors.white, fontSize: 18),
          centerTitle: true,
        ),
      ),
      home: const MyHomePage(title: 'Citabot Home Page'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  String? _token;

  @override
  void initState() {
    super.initState();
    _getTokenAndSend();
  }

  Future<void> _getTokenAndSend() async {
    final token = await FirebaseMessaging.instance.getToken();
    setState(() {
      _token = token;
    });
    debugPrint("FCM Token: $token");
    if (token != null) {
      await sendTokenToBackend(token);
    }
  }

  Future<void> sendTokenToBackend(String token) async {
    final url = Uri.parse(Config.registerTokenUrl);
    try {
      String? userId;
      const int maxRetries = 6;
      for (int i = 0; i < maxRetries; i++) {
        userId = UserService.getUserId();
        if (userId != null) break;
        await Future.delayed(Duration(milliseconds: 500));
      }

      final prefs = await SharedPreferences.getInstance();
      List<String> favoritos = prefs.getStringList('favoritos') ?? [];

      final bodyMap = {
        'token': token,
        if (userId != null) 'user_id': userId,
        if (favoritos.isNotEmpty) 'favoritos': favoritos,
      };

      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: jsonEncode(bodyMap),
      );
      if (response.statusCode == 200) {
        debugPrint("Token enviado correctamente al backend");
      } else {
        debugPrint("Error al enviar token: ${response.statusCode}");
      }
    } catch (e) {
      debugPrint("Error de conexión: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.deepPurple,
        title: const Text('Citabot'),
        centerTitle: true,
        elevation: 4,
      ),
      body: Container(
        width: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Colors.white, Color(0xFFE3D7FF)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Image.asset('assets/images/citabot.png', width: 120, height: 120),
            const SizedBox(height: 16),
            const Text(
              'Bienvenido a Citabot',
              style: TextStyle(
                fontSize: 26,
                fontWeight: FontWeight.bold,
                color: Colors.deepPurple,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              '¿Qué cita quieres buscar?',
              style: TextStyle(fontSize: 18),
            ),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.deepPurple,
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                  vertical: 16,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              icon: const Icon(Icons.car_repair, color: Colors.white),
              label: const Text(
                'Buscar cita ITV',
                style: TextStyle(color: Colors.white, fontSize: 18),
              ),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => FavoritosScreen(estaciones: []),
                  ),
                );
              },
            ),
            const SizedBox(height: 32),
            const Text(
              'Tu token FCM es:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: SelectableText(
                _token ?? 'Obteniendo token...',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12),
              ),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange,
                padding: const EdgeInsets.symmetric(
                  horizontal: 24,
                  vertical: 12,
                ),
              ),
              onPressed: () async {
                if (_token != null) {
                  final url = Uri.parse('${Config.baseUrl}/notifications/test');
                  try {
                    final response = await http.post(
                      url,
                      headers: {"Content-Type": "application/json"},
                      body: jsonEncode({"token": _token}),
                    );
                    if (response.statusCode == 200) {
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Notificación de prueba enviada'),
                          ),
                        );
                      }
                    }
                  } catch (e) {
                    debugPrint("Error enviando notificación de prueba: $e");
                  }
                }
              },
              child: const Text(
                'Probar Notificación',
                style: TextStyle(color: Colors.white),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
