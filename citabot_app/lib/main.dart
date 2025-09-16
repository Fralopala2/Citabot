import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'dart:convert';
import 'horas_disponibles_screen.dart';
import 'config.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  // Inicializa AdMob
  await MobileAds.instance.initialize();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
      ),
      home: const MyHomePage(title: 'Flutter Demo Home Page'),
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
  void mostrarErrorServicios(BuildContext context) {
    if (!mounted) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Error'),
          content: const Text('No se pudieron obtener los servicios para esta estación. Intenta de nuevo más tarde.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cerrar'),
            ),
          ],
        ),
      );
    });
  }

  @override
  void initState() {
    super.initState();
    // Inicializar BannerAd
    _bannerAd = BannerAd(
      adUnitId: 'ca-app-pub-9610124391381160/2707419077',
      size: AdSize.banner,
      request: AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (_) {
          setState(() {
            _isBannerAdReady = true;
          });
        },
        onAdFailedToLoad: (ad, error) {
          ad.dispose();
          debugPrint('Error al cargar banner: \\${error.message}');
        },
      ),
    )..load();
    // Inicializar FCM token
    _getTokenAndSend();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }
  List<dynamic> estaciones = [];
  List<Map<String, dynamic>> tiposVehiculo = [];
  dynamic estacionSeleccionada;
  dynamic tipoSeleccionado;
  bool cargandoEstaciones = false;
  bool cargandoTipos = false;

  Future<void> cargarEstaciones() async {
    setState(() {
      cargandoEstaciones = true;
    });
    final url = Uri.parse(Config.estacionesUrl);
    try {
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        estaciones = data['estaciones'];
      }
    } catch (e) {
      estaciones = [];
    }
    setState(() {
      cargandoEstaciones = false;
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
          mostrarErrorServicios(context);
        }
      } catch (e) {
        tiposVehiculo = [];
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
      '${Config.fechasUrl}?store=$storeId&service=$serviceId&n=3',
    );
    String mensaje = 'No hay fechas disponibles.';
    try {
      final response = await http.get(url);
      if (response.statusCode == 200 && response.body.isNotEmpty) {
        final data = jsonDecode(response.body);
        final fechas = data['fechas'] as List<dynamic>?;
        if (fechas != null && fechas.isNotEmpty) {
          // Mostrar solo fechas válidas (filtrar claves tipo 'n0')
          final fechasValidas = fechas
              .where((f) => f is String && !f.startsWith('n'))
              .toList();
          if (fechasValidas.isNotEmpty) {
            mensaje = 'Fechas disponibles:\n${fechasValidas.join('\n')}';
          }
        }
      }
    } catch (e) {
      mensaje = 'Error de conexion: $e';
    }
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Fechas disponibles'),
        content: Text(mensaje),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cerrar'),
          ),
        ],
      ),
    );
  }

  String? _token;


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
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: '{"token": "$token"}',
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
            // Logo Citabot
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
                    builder: (context) => ITVCitaScreen(token: _token),
                  ),
                );
              },
            ),
            const SizedBox(height: 16),
            if (_isBannerAdReady && _bannerAd != null)
              Container(
                width: _bannerAd!.size.width.toDouble(),
                height: _bannerAd!.size.height.toDouble(),
                alignment: Alignment.center,
                child: AdWidget(ad: _bannerAd!),
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
          ],
        ),
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
  List<dynamic> estaciones = [];
  dynamic estacionSeleccionada;
  List<Map<String, dynamic>> serviciosDisponibles = [];
  dynamic servicioSeleccionado;
  bool cargandoEstaciones = false;
  bool cargandoFechas = false;

  @override
  void initState() {
    super.initState();
    cargarEstaciones();
  }

  Future<void> cargarEstaciones() async {
    setState(() {
      cargandoEstaciones = true;
    });
    final url = Uri.parse(Config.estacionesUrl);
    try {
      final response = await http.get(url);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        estaciones = data['estaciones'];
      }
    } catch (e) {
      estaciones = [];
    }
    setState(() {
      cargandoEstaciones = false;
    });
  }

  Future<void> cargarServiciosDisponibles() async {
    serviciosDisponibles = [];
    if (estacionSeleccionada != null) {
      final storeId = estacionSeleccionada['store_id'];
      final url = Uri.parse('${Config.serviciosUrl}?store_id=$storeId');
      try {
        final response = await http.get(url);
        if (response.statusCode == 200) {
          final data = jsonDecode(response.body);
          serviciosDisponibles = List<Map<String, dynamic>>.from(
            data['servicios'] ?? [],
          );
        }
      } catch (e) {
        serviciosDisponibles = [];
      }
    }
    setState(() {
      servicioSeleccionado = null;
    });
  }

  Future<void> buscarFechas() async {
    if (estacionSeleccionada == null || servicioSeleccionado == null) return;

    // Mostrar indicador de carga
    setState(() {
      cargandoFechas = true;
    });

    final storeId = estacionSeleccionada['store_id'];
    final serviceId = servicioSeleccionado['service'];
    final url = Uri.parse(
      '${Config.fechasUrl}?store=$storeId&service=$serviceId&n=20',
    );

    try {
      final response = await http.get(url);
      if (response.statusCode == 200 && response.body.isNotEmpty) {
        final data = jsonDecode(response.body);
        final fechas = data['fechas_horas'] as List<dynamic>?;
        if (fechas != null && fechas.isNotEmpty) {
          // Agrupar por fecha
          final Map<String, List<Map<String, dynamic>>> agrupadas = {};
          for (var f in fechas) {
            final fecha = f['fecha'] ?? '';
            if (!agrupadas.containsKey(fecha)) agrupadas[fecha] = [];
            agrupadas[fecha]!.add(f);
          }

          // Ocultar indicador de carga antes de navegar
          setState(() {
            cargandoFechas = false;
          });

          if (!mounted) return;
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (context) =>
                  HorasDisponiblesScreen(fechasAgrupadas: agrupadas),
            ),
          );
          return;
        }
      }
    } catch (e) {
      // Mostrar error si es necesario
      debugPrint('Error al buscar fechas: $e');
    }

    // Ocultar indicador de carga
    setState(() {
      cargandoFechas = false;
    });

    if (!mounted) return;
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Fechas disponibles'),
        content: const Text('No hay fechas u horas disponibles.'),
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
        title: const Text('Cita ITV'),
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
            cargandoEstaciones
                ? Column(
                    children: [
                      const CircularProgressIndicator(),
                      const SizedBox(height: 12),
                      const Text(
                        'Cargando estaciones, por favor espera...',
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.deepPurple,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ],
                  )
                : Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0),
                    child: DropdownButton<dynamic>(
                      isExpanded: true,
                      hint: const Text('Selecciona estación'),
                      value: estacionSeleccionada,
                      items: estaciones.map((e) {
                        return DropdownMenuItem(
                          value: e,
                          child: Text(
                            '${e['provincia'] ?? ''} - ${e['nombre'] ?? ''} (${e['tipo'] ?? ''})',
                          ),
                        );
                      }).toList(),
                      onChanged: (value) async {
                        setState(() {
                          estacionSeleccionada = value;
                        });
                        await cargarServiciosDisponibles();
                      },
                    ),
                  ),
            const SizedBox(height: 16),
            estacionSeleccionada == null
                ? const SizedBox.shrink()
                : Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0),
                    child: DropdownButton<dynamic>(
                      isExpanded: true,
                      hint: const Text('Selecciona servicio'),
                      value: servicioSeleccionado,
                      items: serviciosDisponibles.map((t) {
                        return DropdownMenuItem(
                          value: t,
                          child: Text(t['nombre']),
                        );
                      }).toList(),
                      onChanged: (value) {
                        setState(() {
                          servicioSeleccionado = value;
                        });
                      },
                    ),
                  ),
            const SizedBox(height: 16),
            // Mostrar mensaje informativo mientras se carga
            if (cargandoFechas)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
                child: Text(
                  'Consultando disponibilidad en tiempo real...',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.deepPurple,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: cargandoFechas
                    ? Colors.grey
                    : Colors.deepPurple,
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                  vertical: 16,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              icon: cargandoFechas
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.search, color: Colors.white),
              label: Text(
                cargandoFechas ? 'Buscando fechas...' : 'Buscar fechas',
                style: const TextStyle(color: Colors.white, fontSize: 18),
              ),
              onPressed: cargandoFechas ? null : buscarFechas,
            ),
          ],
        ),
      ),
    );
  }
}
