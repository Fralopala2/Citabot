import 'package:flutter/material.dart';

class HorasDisponiblesScreen extends StatelessWidget {
  final Map<String, List<Map<String, dynamic>>> fechasAgrupadas;
  const HorasDisponiblesScreen({super.key, required this.fechasAgrupadas});

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
        children: fechasAgrupadas.entries.map((entry) {
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
                      subtitle: Text('Precio: ${h['precio'] ?? ''}€'),
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}
