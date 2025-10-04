import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

class HorasDisponiblesScreen extends StatefulWidget {
  final Map<String, List<Map<String, dynamic>>> fechasAgrupadas;
  final String? nombreEstacion;
  final bool mostrarPrecio;
  const HorasDisponiblesScreen({
    super.key,
    required this.fechasAgrupadas,
    this.nombreEstacion,
    this.mostrarPrecio = true,
  });

  @override
  State<HorasDisponiblesScreen> createState() => _HorasDisponiblesScreenState();
}

class _HorasDisponiblesScreenState extends State<HorasDisponiblesScreen> {
  BannerAd? _bannerAd;
  bool _isBannerAdReady = false;

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

  // Helper para construir la URL de SITVAL
  String buildSitvalUrl({
    required String store,
    required String service,
    required String date,
  }) {
    return 'https://citaitvsitval.com/?store=$store&service=$service&date=$date';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.deepPurple,
        title: const Text('Horas disponibles'),
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Logo ITV grande y centrado
          Padding(
            padding: const EdgeInsets.only(top: 8.0, bottom: 16.0),
            child: Center(
              child: Image.asset(
                'assets/images/logoITV.png',
                width: 300,
                height: 170,
                fit: BoxFit.contain,
              ),
            ),
          ),
          if (widget.nombreEstacion != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12.0),
              child: Text(
                'Estación: ${widget.nombreEstacion}',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Colors.deepPurple,
                ),
              ),
            ),
          ...widget.fechasAgrupadas.entries.map((entry) {
            final fecha = entry.key;
            final horas = entry.value;
            return Card(
              margin: const EdgeInsets.symmetric(vertical: 8),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      fecha,
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ...horas.map(
                      (h) => ListTile(
                        title: Row(
                          children: [
                            Expanded(child: Text(h['hora'] ?? '')),
                            if (h['store'] != null &&
                                h['service'] != null &&
                                h['fecha'] != null)
                              IconButton(
                                icon: const Icon(
                                  Icons.open_in_new,
                                  size: 18,
                                  color: Colors.deepPurple,
                                ),
                                tooltip: 'Abrir en SITVAL',
                                padding: EdgeInsets.zero,
                                constraints: const BoxConstraints(),
                                onPressed: () async {
                                  final url = buildSitvalUrl(
                                    store: h['store'].toString(),
                                    service: h['service'].toString(),
                                    date: h['fecha'].toString(),
                                  );
                                  final uri = Uri.parse(url);
                                  if (await canLaunchUrl(uri)) {
                                    await launchUrl(
                                      uri,
                                      mode: LaunchMode.externalApplication,
                                    );
                                  }
                                },
                              ),
                          ],
                        ),
                        subtitle:
                            widget.mostrarPrecio &&
                                h['precio'] != null &&
                                h['precio'].toString().isNotEmpty
                            ? Text('Precio: ${h['precio']}€')
                            : null,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }),

          // Banner de anuncios al final
          if (_isBannerAdReady)
            Container(
              alignment: Alignment.center,
              width: _bannerAd!.size.width.toDouble(),
              height: _bannerAd!.size.height.toDouble(),
              margin: const EdgeInsets.only(top: 16),
              child: AdWidget(ad: _bannerAd!),
            ),
        ],
      ),
    );
  }
}
