import 'package:flutter/material.dart';


class HorasDisponiblesScreen extends StatelessWidget {
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
                        title: Text(h['hora'] ?? ''),
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
