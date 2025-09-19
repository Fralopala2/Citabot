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
                // Imagen decorativa ITV
                Padding(
                  padding: const EdgeInsets.only(top: 16.0, bottom: 8.0),
                  child: Image.asset(
                    'assets/images/logoITV.png',
                    width: 220,
                    height: 120,
                    fit: BoxFit.contain,
                  ),
                ),
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
    // Mostrar pantalla de selección de categoría unificada
    final categoriaSeleccionada = await showDialog<String>(
      context: context,
      builder: (context) => SimpleDialog(
        title: const Text('Selecciona tipo de servicio'),
        children: categoriasServicios.keys.map((cat) => SimpleDialogOption(
          child: Text(cat),
          onPressed: () => Navigator.pop(context, cat),
        )).toList(),
      ),
    );
    if (categoriaSeleccionada == null) return;
    setState(() {
      buscandoFavoritos = true;
    });
    final palabrasClave = categoriasServicios[categoriaSeleccionada] ?? [];
    // Depuración: mostrar favoritos y estaciones filtradas
    debugPrint('Favoritos seleccionados: $favoritos');
    final estacionesFiltradas = estaciones.where((e) => favoritos.contains(e['store_id'].toString())).toList();
    debugPrint('Estaciones a consultar: ${estacionesFiltradas.map((e) => e['store_id']).toList()}');

    // Buscar en todas las estaciones favoritas seleccionadas y encontrar la primera fecha global
    DateTime? fechaMinima;
    Map<String, List<Map<String, dynamic>>>? agrupadasMinima;
    String? nombreEstacionMinima;
    for (final estacion in estacionesFiltradas) {
      final storeId = estacion['store_id']?.toString();
      final nombreEstacion = '${estacion['provincia'] ?? ''} - ${estacion['nombre'] ?? ''} (${estacion['tipo'] ?? ''})';
      final urlServicios = Uri.parse('${Config.serviciosUrl}?store_id=$storeId');
      try {
        final responseServicios = await http.get(urlServicios);
        if (responseServicios.statusCode == 200) {
          final dataServicios = jsonDecode(responseServicios.body);
          final servicios = List<Map<String, dynamic>>.from(dataServicios['servicios'] ?? []);
            // Solo buscar servicios equivalentes a la categoría seleccionada
            final serviciosFiltrados = servicios.where((s) {
              final nombre = (s['nombre'] ?? '').toString().toLowerCase();
              return palabrasClave.any((kw) => nombre.contains(kw.toLowerCase()));
            }).toList();
            debugPrint('Estación $storeId ($nombreEstacion) - Servicios equivalentes: ${serviciosFiltrados.map((s) => s['nombre']).toList()}');
          for (final servicio in serviciosFiltrados) {
            final serviceId = servicio['service'];
            if (storeId == null || serviceId == null) continue;
            final urlFechas = Uri.parse('${Config.fechasUrl}?store=$storeId&service=$serviceId&n=10');
            try {
              final responseFechas = await http.get(urlFechas);
              if (responseFechas.statusCode == 200 && responseFechas.body.isNotEmpty) {
                final dataFechas = jsonDecode(responseFechas.body);
                final fechas = dataFechas['fechas_horas'] as List<dynamic>?;
                if (fechas != null && fechas.isNotEmpty) {
                  // Agrupar por fecha
                  final Map<String, List<Map<String, dynamic>>> agrupadas = {};
                  for (var f in fechas) {
                    final fecha = f['fecha'] ?? '';
                    if (!agrupadas.containsKey(fecha)) agrupadas[fecha] = [];
                    agrupadas[fecha]!.add(f);
                  }
                  // Buscar la fecha más próxima de esta estación
                  for (final fechaStr in agrupadas.keys) {
                    try {
                      final dt = DateTime.parse(fechaStr);
                      if (fechaMinima == null || dt.isBefore(fechaMinima)) {
                        fechaMinima = dt;
                        agrupadasMinima = {fechaStr: agrupadas[fechaStr]!};
                        nombreEstacionMinima = nombreEstacion;
                      }
                    } catch (_) {}
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
    setState(() { buscandoFavoritos = false; });
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
    setState(() { buscandoFavoritos = false; });
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (context) => const AlertDialog(
        title: Text('Fechas disponibles'),
        content: Text('No hay fechas u horas disponibles en tus estaciones favoritas para ese servicio.'),
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
          debugPrint('Error al cargar banner (ITVCitaScreen): \\${error.message}');
        },
      ),
    )..load();
  }

  @override
  void dispose() {
    _bannerAd?.dispose();
    super.dispose();
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
      setState(() {
        cargandoEstaciones = false;
      });
    } catch (e) {
      estaciones = [];
      debugPrint('Error al cargar estaciones: $e');
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
                // Botón Buscar en favoritos SIEMPRE debajo del dropdown de servicios
                if (buscandoFavoritos)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
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
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : const Icon(Icons.favorite, color: Colors.white),
                      label: const Text(
                        'Buscar en favoritos',
                        style: TextStyle(color: Colors.white, fontSize: 18),
                      ),
                      onPressed: buscandoFavoritos ? null : buscarPrimeraFechaFavoritos,
                    ),
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
