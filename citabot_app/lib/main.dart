import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
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

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  // Inicializar servicio unificado de usuario (notificaciones + tracking)
  await UserService.initialize();
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
    // El tracking ya se hace automáticamente en UserService.initialize()
    // Get user ID for display
    _getUserId();
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
  bool servidorInicializando = false;
  String mensajeCarga = "Cargando estaciones...";

  Future<bool> _checkServerStatus() async {
    try {
      final baseUrl = Config.estacionesUrl.replaceAll('/itv/estaciones', '');
      final healthUrl = Uri.parse('$baseUrl/health');
      final response = await http.get(healthUrl).timeout(Duration(seconds: 10));

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
      // Si no podemos verificar el estado, asumimos que está inicializando
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

    // Verificar estado del servidor
    final serverReady = await _checkServerStatus();

    if (!serverReady) {
      // Si el servidor no está listo, intentar cada 5 segundos hasta que esté listo
      await _waitForServerReady();
    }

    final url = Uri.parse(Config.estacionesUrl);
    try {
      setState(() {
        mensajeCarga = "Cargando estaciones...";
        servidorInicializando = false;
      });

      final response = await http.get(url).timeout(Duration(seconds: 15));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        estaciones = data['estaciones'];

        // Mostrar mensaje de éxito brevemente
        setState(() {
          mensajeCarga = "¡Estaciones cargadas correctamente!";
        });

        // Esperar un momento para mostrar el mensaje de éxito
        await Future.delayed(Duration(milliseconds: 1000));
      } else {
        throw Exception('Error del servidor: ${response.statusCode}');
      }
    } catch (e) {
      estaciones = [];
      setState(() {
        mensajeCarga = "Error al cargar estaciones. Reintentando...";
      });

      // Reintentar después de 3 segundos
      Future.delayed(Duration(seconds: 3), () {
        if (mounted) cargarEstaciones();
      });
    }

    setState(() {
      cargandoEstaciones = false;
    });
  }

  Future<void> _waitForServerReady() async {
    int maxRetries = 24; // 24 * 5 segundos = 2 minutos máximo
    int retries = 0;

    while (retries < maxRetries) {
      await Future.delayed(Duration(seconds: 5));

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

    // Si llegamos aquí, el servidor tardó demasiado
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

    String mensaje = 'No hay fechas disponibles.';

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
        // FIX: Use 'fechas_horas' not 'fechas' to match backend response
        final fechas = data['fechas_horas'] as List<dynamic>?;

        if (fechas != null && fechas.isNotEmpty) {
          // Group by date and show formatted
          final Map<String, List<String>> fechasPorDia = {};
          for (var f in fechas) {
            final fecha = f['fecha'] ?? '';
            final hora = f['hora'] ?? '';
            if (fecha.isNotEmpty && hora.isNotEmpty) {
              if (!fechasPorDia.containsKey(fecha)) fechasPorDia[fecha] = [];
              fechasPorDia[fecha]!.add(hora);
            }
          }

          if (fechasPorDia.isNotEmpty) {
            final buffer = StringBuffer();
            fechasPorDia.forEach((fecha, horas) {
              buffer.writeln('$fecha:');
              for (String hora in horas) {
                buffer.writeln('  • $hora');
              }
              buffer.writeln();
            });
            mensaje = buffer.toString().trim();
          }
        }
      }
    } catch (e) {
      mensaje = 'Error de conexión: $e';
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
  String? _userId;

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

  Future<void> _getUserId() async {
    try {
      final userId = UserService.getUserId();
      setState(() {
        _userId = userId;
      });
    } catch (e) {
      debugPrint("Error getting user ID: $e");
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
                const SizedBox(height: 16),
                const Text(
                  'Tu User ID (para soporte):',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0),
                  child: SelectableText(
                    _userId ?? 'Obteniendo ID...',
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 12,
                      color: Colors.deepPurple,
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                // El banner se elimina de aquí
              ],
            ),
          ),
          if (_isBannerAdReady && _bannerAd != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 24, // margen para no tapar la barra del sistema
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
  Future<List<String>> _getFavoritos() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList('favoritos') ?? [];
  }

  bool buscandoFavoritos = false;
  String? nombreEstacionEncontrada;
  Future<void> buscarPrimeraFechaFavoritos() async {
    // 1. Seleccionar servicio unificado antes de buscar
    final favoritos = await _getFavoritos();
    if (!mounted) return;

    if (favoritos.isEmpty) {
      showDialog(
        context: context,
        builder: (context) => const AlertDialog(
          title: Text('Favoritos no seleccionados'),
          content: Text('Selecciona al menos una estación favorita.'),
        ),
      );
      return;
    }
    // Selector de categoría: solo 'Turismo' (una vez) y el resto de categorías (sin variantes de turismo)
    final List<String> categoriasOriginal = categoriasServicios.keys.toList();
    final List<String> turismoVariantes = [
      'Turismo diésel',
      'Turismo gasolina',
      'Turismo eléctrico',
    ]; // variantes a agrupar
    final List<String> categorias = [
      'Turismo',
      ...categoriasOriginal.where(
        (c) => !turismoVariantes.contains(c) && c.toLowerCase() != 'turismo',
      ),
    ];
    final categoriaSeleccionada = await showDialog<String>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Selecciona tipo de servicio'),
        children: categorias
            .map(
              (cat) => SimpleDialogOption(
                child: Text(cat),
                onPressed: () => Navigator.pop(context, cat),
              ),
            )
            .toList(),
      ),
    );
    if (!mounted) return;
    if (categoriaSeleccionada == null) return;

    // Si es 'Turismo', mostrar subtipo
    String? subtipoSeleccionado;
    if (categoriaSeleccionada == 'Turismo') {
      final List<String> subtipos = ['diésel', 'gasolina', 'eléctrico'];
      subtipoSeleccionado = await showDialog<String>(
        context: context,
        builder: (context) => SimpleDialog(
          title: const Text('Selecciona subtipo de Turismo'),
          children: subtipos
              .map(
                (sub) => SimpleDialogOption(
                  child: Text(sub[0].toUpperCase() + sub.substring(1)),
                  onPressed: () => Navigator.pop(context, sub),
                ),
              )
              .toList(),
        ),
      );
      if (!mounted) return;
      if (subtipoSeleccionado == null) return;
    }

    setState(() {
      buscandoFavoritos = true;
    });
    debugPrint('Favoritos seleccionados (raw): $favoritos');
    final favoritosSet = favoritos.map((f) => f.toString()).toSet();
    final estacionesFiltradas = estaciones
        .where((e) => favoritosSet.contains(e['store_id'].toString()))
        .toList();
    debugPrint(
      'Estaciones filtradas (solo favoritas): ${estacionesFiltradas.map((e) => e['store_id']).toList()}',
    );

    DateTime? fechaMinima;
    Map<String, List<Map<String, dynamic>>>? agrupadasMinima;
    String? nombreEstacionMinima;
    String normalizar(String s) => s
        .toLowerCase()
        .replaceAll('á', 'a')
        .replaceAll('é', 'e')
        .replaceAll('í', 'i')
        .replaceAll('ó', 'o')
        .replaceAll('ú', 'u')
        .replaceAll('ü', 'u')
        .replaceAll(' ', '');
    String? subtipoNorm = subtipoSeleccionado != null
        ? normalizar(subtipoSeleccionado)
        : null;
    String catNorm = normalizar(categoriaSeleccionada);
    for (final estacion in estacionesFiltradas) {
      final storeIdFav = estacion['store_id']?.toString();
      final nombreEstacionFav =
          '${estacion['provincia'] ?? ''} - ${estacion['nombre'] ?? ''} (${estacion['tipo'] ?? ''})';
      final urlServicios = Uri.parse(
        '${Config.serviciosUrl}?store_id=$storeIdFav',
      );
      try {
        final responseServicios = await http.get(urlServicios);
        if (responseServicios.statusCode == 200) {
          final dataServicios = jsonDecode(responseServicios.body);
          final servicios = List<Map<String, dynamic>>.from(
            dataServicios['servicios'] ?? [],
          );
          debugPrint(
            'Estación $storeIdFav ($nombreEstacionFav) - TODOS los servicios:',
          );
          for (final s in servicios) {
            debugPrint('  Servicio: "${s['nombre']}"');
          }
          // Filtrar servicios según selección
          final serviciosFiltrados = servicios.where((s) {
            final nombre = normalizar((s['nombre'] ?? '').toString());
            if (subtipoNorm != null) {
              // Si es turismo, aceptar solo servicios que contengan el subtipo y NO palabras excluidas
              final exclusiones = [
                'cuadriciclo',
                'quad',
                'moto',
                'motocicleta',
                'remolque',
                'camion',
                'autobus',
                'tractor',
                'obras',
                'servicios',
                'agricola',
                've',
                'caravana',
                'autocaravana',
                'bus',
                'furgoneta',
                'ligero',
                'semirremolque',
              ];
              final esExcluido = exclusiones.any((pal) => nombre.contains(pal));
              return nombre.contains(subtipoNorm) && !esExcluido;
            } else {
              // Buscar por categoría seleccionada
              return nombre.contains(catNorm);
            }
          }).toList();
          debugPrint(
            'Estación $storeIdFav ($nombreEstacionFav) - Servicios válidos: ${serviciosFiltrados.map((s) => s['nombre']).toList()}',
          );
          for (final servicio in serviciosFiltrados) {
            final serviceId = servicio['service'];
            if (storeIdFav == null || serviceId == null) continue;
            final urlFechas = Uri.parse(
              '${Config.fechasUrl}?store=$storeIdFav&service=$serviceId&n=10',
            );
            try {
              final responseFechas = await http.get(
                urlFechas,
                headers: {
                  'Cache-Control': 'no-cache, no-store, must-revalidate',
                  'Pragma': 'no-cache',
                  'Expires': '0',
                },
              );
              if (responseFechas.statusCode == 200 &&
                  responseFechas.body.isNotEmpty) {
                debugPrint('=== RESPONSE DEBUG ===');
                debugPrint('URL: ${urlFechas.toString()}');
                debugPrint('Status: ${responseFechas.statusCode}');
                debugPrint('Body: ${responseFechas.body}');

                final dataFechas = jsonDecode(responseFechas.body);
                final fechas = dataFechas['fechas_horas'] as List<dynamic>?;
                debugPrint('Fechas parsed: $fechas');

                if (fechas != null && fechas.isNotEmpty) {
                  final Map<String, List<Map<String, dynamic>>> agrupadas = {};
                  for (var f in fechas) {
                    final fecha = f['fecha'] ?? '';
                    if (!agrupadas.containsKey(fecha)) agrupadas[fecha] = [];
                    agrupadas[fecha]!.add(f);
                  }
                  final hoy = DateTime.now();
                  for (final fechaStr in agrupadas.keys) {
                    try {
                      final dt = DateTime.parse(fechaStr);
                      debugPrint('Evaluando fecha: $fechaStr -> $dt');
                      if (dt.isBefore(DateTime(hoy.year, hoy.month, hoy.day))) {
                        debugPrint('Fecha $fechaStr es del pasado, ignorando');
                        continue;
                      }
                      if (fechaMinima == null || dt.isBefore(fechaMinima)) {
                        debugPrint(
                          'Nueva fecha mínima: $fechaStr (anterior: $fechaMinima)',
                        );
                        fechaMinima = dt;
                        agrupadasMinima = {fechaStr: agrupadas[fechaStr]!};
                        nombreEstacionMinima = nombreEstacionFav;
                      }
                    } catch (e) {
                      debugPrint('Error parsing fecha $fechaStr: $e');
                    }
                  }
                }
              }
            } catch (e) {
              debugPrint('Error al buscar fechas: $e');
            }
          }
        }
      } catch (e) {
        debugPrint('Error al buscar servicios: $e');
      }
    }
    setState(() {
      buscandoFavoritos = false;
    });
    if (agrupadasMinima != null && nombreEstacionMinima != null) {
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (context) => HorasDisponiblesScreen(
            fechasAgrupadas: agrupadasMinima!,
            nombreEstacion: nombreEstacionMinima,
            mostrarPrecio: false,
          ),
        ),
      );
      return;
    }
    setState(() {
      buscandoFavoritos = false;
    });
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (context) => const AlertDialog(
        title: Text('Fechas disponibles'),
        content: Text(
          'No hay fechas u horas disponibles en tus estaciones favoritas para ese servicio.',
        ),
      ),
    );
  }

  BannerAd? _bannerAd;
  bool _isBannerAdReady = false;
  List<dynamic> estaciones = [];
  dynamic estacionSeleccionada;
  List<Map<String, dynamic>> serviciosDisponibles = [];
  dynamic servicioSeleccionado;
  bool cargandoEstaciones = false;
  bool cargandoFechas = false;
  bool servidorInicializando = false;
  String mensajeCarga = "Cargando estaciones...";

  @override
  void initState() {
    super.initState();
    cargarEstaciones();
    _bannerAd = BannerAd(
      adUnitId: 'ca-app-pub-9610124391381160/8625088028',
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
          debugPrint(
            'Error al cargar banner (ITVCitaScreen): \\${error.message}',
          );
        },
      ),
    )..load();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
  }

  Future<bool> _checkServerStatus() async {
    try {
      final baseUrl = Config.estacionesUrl.replaceAll('/itv/estaciones', '');
      final healthUrl = Uri.parse('$baseUrl/health');
      final response = await http.get(healthUrl).timeout(Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final serverReady = data['server_ready'] ?? false;

        if (mounted) {
          setState(() {
            servidorInicializando = !serverReady;
            if (servidorInicializando) {
              mensajeCarga =
                  "El servidor se está inicializando...\nEsto puede tardar hasta 1 minuto.";
            } else {
              mensajeCarga = "Cargando estaciones...";
            }
          });
        }

        return serverReady;
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          servidorInicializando = true;
          mensajeCarga =
              "Conectando con el servidor...\nEsto puede tardar hasta 1 minuto.";
        });
      }
    }
    return false;
  }

  Future<void> _waitForServerReady() async {
    int maxRetries = 24;
    int retries = 0;

    while (retries < maxRetries && mounted) {
      await Future.delayed(Duration(seconds: 5));

      if (!mounted) return; // Exit if widget is disposed

      final serverReady = await _checkServerStatus();
      if (serverReady) {
        if (mounted) {
          setState(() {
            servidorInicializando = false;
            mensajeCarga = "¡Servidor listo! Cargando estaciones...";
          });
        }
        return;
      }

      retries++;
      if (mounted) {
        setState(() {
          mensajeCarga =
              "El servidor se está inicializando...\nReintentando en 5 segundos... ($retries/$maxRetries)";
        });
      }
    }

    if (mounted) {
      setState(() {
        servidorInicializando = false;
        mensajeCarga =
            "El servidor está tardando más de lo esperado. Reintentando...";
      });
    }
  }

  Future<void> cargarEstaciones() async {
    if (!mounted) return;

    setState(() {
      cargandoEstaciones = true;
      mensajeCarga = "Conectando...";
    });

    // Verificar estado del servidor
    final serverReady = await _checkServerStatus();

    if (!serverReady && mounted) {
      await _waitForServerReady();
    }

    final url = Uri.parse(Config.estacionesUrl);
    try {
      setState(() {
        mensajeCarga = "Cargando estaciones...";
        servidorInicializando = false;
      });

      final response = await http.get(url).timeout(Duration(seconds: 15));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        estaciones = data['estaciones'];

        if (mounted) {
          setState(() {
            mensajeCarga = "¡Estaciones cargadas correctamente!";
          });
        }

        await Future.delayed(Duration(milliseconds: 1000));
      } else {
        throw Exception('Error del servidor: ${response.statusCode}');
      }
    } catch (e) {
      estaciones = [];
      debugPrint('Error al cargar estaciones: $e');
      if (mounted) {
        setState(() {
          mensajeCarga = "Error al cargar estaciones. Reintentando...";
        });
      }

      Future.delayed(Duration(seconds: 3), () {
        if (mounted) cargarEstaciones();
      });
    }

    if (mounted) {
      setState(() {
        cargandoEstaciones = false;
      });
    }
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
        setState(() {
          servicioSeleccionado = null;
        });
      } catch (e) {
        serviciosDisponibles = [];
        debugPrint('Error al cargar servicios: $e');
        setState(() {
          servicioSeleccionado = null;
        });
      }
    } else {
      setState(() {
        servicioSeleccionado = null;
      });
    }
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
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.favorite, color: Colors.white),
            tooltip: 'Gestionar favoritos',
            onPressed: () async {
              await Navigator.push(
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
                // Logo ITV grande y centrado
                Padding(
                  padding: const EdgeInsets.only(top: 24.0, bottom: 16.0),
                  child: Center(
                    child: Image.asset(
                      'assets/images/logoITV.png',
                      width: 300,
                      height: 170,
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
                cargandoEstaciones
                    ? Column(
                        children: [
                          CircularProgressIndicator(
                            color: servidorInicializando
                                ? Colors.orange
                                : Colors.deepPurple,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            mensajeCarga,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 14,
                              color: servidorInicializando
                                  ? Colors.orange[700]
                                  : Colors.deepPurple,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                          if (servidorInicializando) ...[
                            const SizedBox(height: 8),
                            Text(
                              '⏱️ Render está iniciando el servidor...',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 12,
                                color: Colors.grey[600],
                              ),
                            ),
                          ],
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
                // Botón Buscar en favoritos SIEMPRE debajo del dropdown de servicios
                if (buscandoFavoritos)
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16.0,
                      vertical: 8.0,
                    ),
                    child: Text(
                      'Buscando fechas entre las estaciones favoritas...',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 14,
                        color: Colors.deepPurple,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32.0),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.pink,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 32,
                          vertical: 16,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      icon: buscandoFavoritos
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.5,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  Colors.white,
                                ),
                              ),
                            )
                          : const Icon(Icons.favorite, color: Colors.white),
                      label: const Text(
                        'Buscar en favoritos',
                        style: TextStyle(color: Colors.white, fontSize: 18),
                      ),
                      onPressed: buscandoFavoritos
                          ? null
                          : buscarPrimeraFechaFavoritos,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                // Mostrar mensaje informativo mientras se carga
                if (cargandoFechas)
                  const Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: 16.0,
                      vertical: 8.0,
                    ),
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
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32.0),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
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
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  Colors.white,
                                ),
                              ),
                            )
                          : const Icon(Icons.search, color: Colors.white),
                      label: Text(
                        cargandoFechas ? 'Buscando fechas...' : 'Buscar fechas',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                        ),
                      ),
                      onPressed: cargandoFechas ? null : buscarFechas,
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                // El banner se elimina de aquí
              ],
            ),
          ),
          if (_isBannerAdReady && _bannerAd != null)
            Positioned(
              left: 0,
              right: 0,
              bottom: 24, // margen para no tapar la barra del sistema
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
