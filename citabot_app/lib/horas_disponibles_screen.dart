import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';


class HorasDisponiblesScreen extends StatelessWidget {
  // Helper para construir la URL de SITVAL
  String buildSitvalUrl({required String store, required String service, required String date}) {
    // Ahora usando el dominio correcto:
    // https://citaitvsitval.com/?store=18&service=275&date=2025-09-29
    return 'https://citaitvsitval.com/?store=$store&service=$service&date=$date';
  }
  final Map<String, List<Map<String, dynamic>>> fechasAgrupadas;
  final String? nombreEstacion;
  final bool mostrarPrecio;
  const HorasDisponiblesScreen({super.key, required this.fechasAgrupadas, this.nombreEstacion, this.mostrarPrecio = true});

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
          if (nombreEstacion != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12.0),
              child: Text(
                'Estación: $nombreEstacion',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  color: Colors.deepPurple,
                ),
              ),
            ),
          ...fechasAgrupadas.entries.map((entry) {
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
                            if (h['store'] != null && h['service'] != null && h['fecha'] != null)
                              IconButton(
                                icon: const Icon(Icons.open_in_new, size: 18, color: Colors.deepPurple),
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
                                    await launchUrl(uri, mode: LaunchMode.externalApplication);
                                  }
                                },
                              ),
                          ],
                        ),
                        subtitle: mostrarPrecio && h['precio'] != null && h['precio'].toString().isNotEmpty
                            ? Text('Precio: ${h['precio']}€')
                            : null,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        ],
      ),
    );
  }
}
