import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'horas_disponibles_screen.dart';
import 'config.dart';
import 'favoritos_screen.dart';
import 'categorias_servicio.dart';
import 'services/user_service.dart';

// Plugin de notificaciones locales
final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
    FlutterLocalNotificationsPlugin();

// Handler global para notificaciones en background
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  debugPrint('📨 Background message received: ${message.notification?.title}');
  await _showLocalNotification(message);
}

// Funcion para inicializar notificaciones locales
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

  // Configurar edge-to-edge display
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);

  // Configurar colores transparentes para las barras del sistema
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      systemNavigationBarColor: Colors.transparent,
      systemNavigationBarIconBrightness: Brightness.dark,
    ),
  );

  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  await _initializeLocalNotifications();

  runApp(const MyApp());

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
  BannerAd? _bannerAd;
  bool _isBannerAdReady = false;
  String? _token;

  @override
  void initState() {
    super.initState();
    _bannerAd = BannerAd(
      adUnitId: 'ca-app-pub-9610124391381160/2707419077',
      size: AdSize.banner,
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (_) {
          setState(() {
            _isBannerAdReady = true;
          });
        },
        onAdFailedToLoad: (ad, error) {
          ad.dispose();
          debugPrint('Error al cargar banner: ${error.message}');
        },
      ),
    )..load();

    _getTokenAndSend();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
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
        await Future.delayed(const Duration(milliseconds: 500));
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
      body: Stack(
        children: [
          Container(
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
                // Logo Citabot
                Image.asset(
                  'assets/images/citabot.png',
                  width: 120,
                  height: 120,
                ),
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
                        builder: (context) => ITVCitaScreen(token: _token),
                      ),
                    );
                  },
                ),
                const SizedBox(height: 16),
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
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32.0),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.grey[800],
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      icon: const Icon(
                        Icons.notifications_off,
                        color: Colors.white,
                      ),
                      label: const Text(
                        'Dejar de recibir notificaciones',
                        style: TextStyle(color: Colors.white),
                      ),
                      onPressed: () async {
                        final confirmed = await showDialog<bool>(
                          context: context,
                          builder: (context) => AlertDialog(
                            title: const Text('Confirmar baja'),
                            content: const Text(
                              '¿Estás seguro de que quieres dejar de recibir notificaciones?',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () =>
                                    Navigator.of(context).pop(false),
                                child: const Text('Cancelar'),
                              ),
                              ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.red,
                                ),
                                onPressed: () =>
                                    Navigator.of(context).pop(true),
                                child: const Text('Sí, darme de baja'),
                              ),
                            ],
                          ),
                        );

                        if (confirmed != true) return;
                        if (!mounted) return;

                        final scaffold = ScaffoldMessenger.of(context);
                        scaffold.showSnackBar(
                          const SnackBar(content: Text('Procesando baja...')),
                        );
                        final success =
                            await UserService.unsubscribeFromNotifications();
                        if (!mounted) return;
                        scaffold.hideCurrentSnackBar();
                        if (success) {
                          scaffold.showSnackBar(
                            const SnackBar(
                              content: Text(
                                'Te has dado de baja de las notificaciones',
                              ),
                            ),
                          );
                          setState(() {
                            _token = null;
                          });
                        } else {
                          scaffold.showSnackBar(
                            const SnackBar(
                              content: Text(
                                'No se pudo procesar la baja, inténtalo más tarde',
                              ),
                            ),
                          );
                        }
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32.0),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green[700],
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 12,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      icon: const Icon(Icons.refresh, color: Colors.white),
                      label: const Text(
                        'Volver a suscribirse',
                        style: TextStyle(color: Colors.white),
                      ),
                      onPressed: () async {
                        final scaffold = ScaffoldMessenger.of(context);
                        scaffold.showSnackBar(
                          const SnackBar(content: Text('Re-suscribiendo...')),
                        );
                        await UserService.refreshToken();
                        if (!mounted) return;
                        scaffold.hideCurrentSnackBar();
                        final token = UserService.getCurrentToken();
                        if (token != null) {
                          scaffold.showSnackBar(
                            const SnackBar(
                              content: Text(
                                'Te has vuelto a suscribir a las notificaciones',
                              ),
                            ),
                          );
                          if (!mounted) return;
                          setState(() {
                            _token = token;
                          });
                        } else {
                          scaffold.showSnackBar(
                            const SnackBar(
                              content: Text(
                                'No se pudo re-suscribir, inténtalo más tarde',
                              ),
                            ),
                          );
                        }
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (_isBannerAdReady && _bannerAd != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: MediaQuery.of(context).viewPadding.bottom + 4,
              child: Container(
                width: _bannerAd!.size.width.toDouble(),
                height: _bannerAd!.size.height.toDouble(),
                alignment: Alignment.center,
                child: AdWidget(ad: _bannerAd!),
              ),
            ),
        ],
      ),
    );
  }
}

class ITVCitaScreen extends StatefulWidget {
  final String? token;
  const ITVCitaScreen({super.key, this.token});

  @override
  State<ITVCitaScreen> createState() => _ITVCitaScreenState();
}

class _ITVCitaScreenState extends State<ITVCitaScreen> {
  BannerAd? _bannerAd;
  bool _isBannerAdReady = false;
  List<dynamic> estaciones = [];
  List<Map<String, dynamic>> tiposVehiculo = [];
  dynamic estacionSeleccionada;
  dynamic tipoSeleccionado;
  bool cargandoEstaciones = false;
  bool cargandoTipos = false;
  bool servidorInicializando = false;
  String mensajeCarga = "Cargando estaciones...";

  @override
  void initState() {
    super.initState();
    _bannerAd = BannerAd(
      adUnitId: 'ca-app-pub-9610124391381160/2707419077',
      size: AdSize.banner,
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (_) {
          setState(() {
            _isBannerAdReady = true;
          });
        },
        onAdFailedToLoad: (ad, error) {
          ad.dispose();
          debugPrint('Error al cargar banner: ${error.message}');
        },
      ),
    )..load();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }

  void mostrarErrorServicios(BuildContext context) {
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Error'),
        content: const Text(
          'No se pudieron obtener los servicios para esta estación. Intenta de nuevo más tarde.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  Future<bool> _checkServerStatus() async {
    try {
      final baseUrl = Config.estacionesUrl.replaceAll('/itv/estaciones', '');
      final healthUrl = Uri.parse('$baseUrl/health');
      final response = await http
          .get(healthUrl)
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final serverReady = data['server_ready'] ?? false;
        final stationsAvailable = data['stations_available'] ?? false;

        if (mounted) {
          setState(() {
            servidorInicializando = !serverReady;
            if (!serverReady) {
              mensajeCarga =
                  "El servidor se está inicializando...\nEsto puede tardar hasta 2 minutos.";
            } else if (!stationsAvailable) {
              mensajeCarga = "Servidor listo, cargando estaciones...";
            } else {
              mensajeCarga = "Cargando estaciones...";
            }
          });
        }

        return serverReady && stationsAvailable;
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          servidorInicializando = true;
          mensajeCarga =
              "Conectando con el servidor...\nEsto puede tardar hasta 2 minutos.";
        });
      }
    }
    return false;
  }

  Future<void> cargarEstaciones() async {
    setState(() {
      cargandoEstaciones = true;
      mensajeCarga = "Conectando...";
    });

    final serverReady = await _checkServerStatus();

    if (!serverReady) {
      await _waitForServerReady();
    }

    final url = Uri.parse(Config.estacionesUrl);
    try {
      setState(() {
        mensajeCarga = "Cargando estaciones...";
        servidorInicializando = false;
      });

      final response = await http.get(url).timeout(const Duration(seconds: 15));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        estaciones = data['estaciones'];

        setState(() {
          mensajeCarga = "¡Estaciones cargadas correctamente!";
        });

        await Future.delayed(const Duration(milliseconds: 1000));
      } else {
        throw Exception('Error del servidor: ${response.statusCode}');
      }
    } catch (e) {
      estaciones = [];
      setState(() {
        mensajeCarga = "Error al cargar estaciones. Reintentando...";
      });

      Future.delayed(const Duration(seconds: 3), () {
        if (mounted) cargarEstaciones();
      });
    }

    setState(() {
      cargandoEstaciones = false;
    });
  }

  Future<void> _waitForServerReady() async {
    int maxRetries = 24;
    int retries = 0;

    while (retries < maxRetries) {
      await Future.delayed(const Duration(seconds: 5));

      final serverReady = await _checkServerStatus();
      if (serverReady) {
        setState(() {
          servidorInicializando = false;
          mensajeCarga = "¡Servidor listo! Cargando estaciones...";
        });
        return;
      }

      retries++;
      setState(() {
        mensajeCarga =
            "El servidor se está inicializando...\nReintentando en 5 segundos... ($retries/$maxRetries)";
      });
    }

    setState(() {
      servidorInicializando = false;
      mensajeCarga =
          "El servidor está tardando más de lo esperado. Reintentando...";
    });
  }

  Future<void> cargarTiposVehiculo() async {
    tiposVehiculo = [];
    if (estacionSeleccionada != null) {
      final storeId = estacionSeleccionada['store_id'];
      final url = Uri.parse('${Config.serviciosUrl}?store_id=$storeId');
      try {
        final response = await http.get(url);
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          tiposVehiculo = List<Map<String, dynamic>>.from(
            data['servicios'] ?? [],
          );
        } else {
          tiposVehiculo = [];
          if (!mounted) return;
          mostrarErrorServicios(context);
        }
      } catch (e) {
        tiposVehiculo = [];
        if (!mounted) return;
        mostrarErrorServicios(context);
      }
    }
    setState(() {
      tipoSeleccionado = null;
    });
  }

  Future<void> buscarFechas() async {
    if (estacionSeleccionada == null || tipoSeleccionado == null) return;

    final storeId = estacionSeleccionada['store_id'];
    final serviceId = tipoSeleccionado['service'];
    final url = Uri.parse(
      '${Config.fechasUrl}?store=$storeId&service=$serviceId&n=10',
    );

    List<Map<String, dynamic>> fechasDisponibles = [];

    try {
      final response = await http.get(
        url,
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
        },
      );

      if (response.statusCode == 200 && response.body.isNotEmpty) {
        final data = jsonDecode(response.body);
        final fechas = data['fechas_horas'] as List<dynamic>?;

        if (fechas != null && fechas.isNotEmpty) {
          for (var f in fechas) {
            final fecha = f['fecha'] ?? '';
            final hora = f['hora'] ?? '';
            if (fecha.isNotEmpty && hora.isNotEmpty) {
              fechasDisponibles.add({
                'fecha': fecha,
                'hora': hora,
                'store': storeId,
                'service': serviceId,
              });
            }
          }
        }
      }
    } catch (e) {
      debugPrint('Error de conexión: $e');
    }

    if (!mounted) return;

    if (fechasDisponibles.isEmpty) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Sin fechas disponibles'),
          content: const Text(
            'No hay fechas disponibles para esta estación y servicio.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cerrar'),
            ),
          ],
        ),
      );
      return;
    }

    // Agrupar por fecha
    final Map<String, List<Map<String, dynamic>>> fechasPorDia = {};
    for (var cita in fechasDisponibles) {
      final fecha = cita['fecha'];
      if (!fechasPorDia.containsKey(fecha)) fechasPorDia[fecha] = [];
      fechasPorDia[fecha]!.add(cita);
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Fechas disponibles'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView(
            shrinkWrap: true,
            children: fechasPorDia.entries.map((entry) {
              final fecha = entry.key;
              final citas = entry.value;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8.0),
                    child: Text(
                      fecha,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                  ),
                  ...citas.map(
                    (cita) => ListTile(
                      dense: true,
                      title: Text(cita['hora']),
                      trailing: IconButton(
                        icon: const Icon(
                          Icons.open_in_new,
                          color: Colors.deepPurple,
                        ),
                        tooltip: 'Reservar cita',
                        onPressed: () async {
                          final reservaUrl =
                              'https://citaitvsitval.com/?store=${cita['store']}&service=${cita['service']}&date=${cita['fecha']}';
                          final uri = Uri.parse(reservaUrl);
                          if (await canLaunchUrl(uri)) {
                            await launchUrl(
                              uri,
                              mode: LaunchMode.externalApplication,
                            );
                          }
                        },
                      ),
                    ),
                  ),
                  const Divider(),
                ],
              );
            }).toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.deepPurple,
        title: const Text('Buscar Cita ITV'),
        centerTitle: true,
        elevation: 4,
        actions: [
          IconButton(
            icon: const Icon(Icons.favorite, color: Colors.white),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => FavoritosScreen(estaciones: estaciones),
                ),
              );
            },
          ),
        ],
      ),
      body: Stack(
        children: [
          Container(
            width: double.infinity,
            height: double.infinity,
            decoration: const BoxDecoration(color: Color(0xFFE8E8E8)),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Logo ITV grande y centrado
                  Padding(
                    padding: const EdgeInsets.only(top: 8.0, bottom: 24.0),
                    child: Center(
                      child: Image.asset(
                        'assets/images/logoITV.png',
                        width: 300,
                        height: 170,
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),

                  // Botón para cargar estaciones
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: cargandoEstaciones
                          ? Colors.grey[600]
                          : Colors.deepPurple,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    icon: const Icon(Icons.refresh, color: Colors.white),
                    label: Text(
                      cargandoEstaciones
                          ? mensajeCarga
                          : 'Cargar Estaciones ITV',
                      style: const TextStyle(color: Colors.white, fontSize: 16),
                    ),
                    onPressed: cargandoEstaciones ? null : cargarEstaciones,
                  ),

                  const SizedBox(height: 20),

                  // Dropdown de estaciones
                  if (estaciones.isNotEmpty) ...[
                    const Text(
                      'Selecciona una estación:',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey),
                        borderRadius: BorderRadius.circular(8),
                        color: Colors.white,
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<dynamic>(
                          value: estacionSeleccionada,
                          hint: const Text('Selecciona una estación'),
                          isExpanded: true,
                          items: estaciones.map<DropdownMenuItem<dynamic>>((
                            estacion,
                          ) {
                            final nombre =
                                '${estacion['provincia'] ?? ''} - ${estacion['nombre'] ?? ''} (${estacion['tipo'] ?? ''})';
                            return DropdownMenuItem<dynamic>(
                              value: estacion,
                              child: Text(
                                nombre,
                                overflow: TextOverflow.ellipsis,
                              ),
                            );
                          }).toList(),
                          onChanged: (value) {
                            setState(() {
                              estacionSeleccionada = value;
                              tipoSeleccionado = null;
                              tiposVehiculo = [];
                            });
                            if (value != null) {
                              cargarTiposVehiculo();
                            }
                          },
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  // Dropdown de tipos de vehículo
                  if (tiposVehiculo.isNotEmpty) ...[
                    const Text(
                      'Selecciona el tipo de servicio:',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey),
                        borderRadius: BorderRadius.circular(8),
                        color: Colors.white,
                      ),
                      child: DropdownButtonHideUnderline(
                        child: DropdownButton<dynamic>(
                          value: tipoSeleccionado,
                          hint: const Text('Selecciona un servicio'),
                          isExpanded: true,
                          items: tiposVehiculo.map<DropdownMenuItem<dynamic>>((
                            tipo,
                          ) {
                            return DropdownMenuItem<dynamic>(
                              value: tipo,
                              child: Text(
                                tipo['nombre'] ?? '',
                                overflow: TextOverflow.ellipsis,
                              ),
                            );
                          }).toList(),
                          onChanged: (value) {
                            setState(() {
                              tipoSeleccionado = value;
                            });
                          },
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  // Botón de buscar fechas
                  if (estacionSeleccionada != null && tipoSeleccionado != null)
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      icon: const Icon(Icons.search, color: Colors.white),
                      label: const Text(
                        'Buscar Fechas Disponibles',
                        style: TextStyle(color: Colors.white, fontSize: 16),
                      ),
                      onPressed: buscarFechas,
                    ),
                  const SizedBox(height: 80), // Espacio para el banner
                ],
              ),
            ),
          ),
          // Banner publicitario
          if (_isBannerAdReady && _bannerAd != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: MediaQuery.of(context).viewPadding.bottom + 4,
              child: Container(
                width: _bannerAd!.size.width.toDouble(),
                height: _bannerAd!.size.height.toDouble(),
                alignment: Alignment.center,
                child: AdWidget(ad: _bannerAd!),
              ),
            ),
        ],
      ),
    );
  }
}
