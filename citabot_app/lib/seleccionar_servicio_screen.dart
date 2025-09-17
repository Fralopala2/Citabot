import 'package:flutter/material.dart';


class SeleccionarServicioScreen extends StatelessWidget {
  final List<Map<String, dynamic>> servicios;
  const SeleccionarServicioScreen({super.key, required this.servicios});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Selecciona tipo de servicio'),
        backgroundColor: Colors.deepPurple,
      ),
      body: ListView.builder(
        itemCount: servicios.length,
        itemBuilder: (context, index) {
          final servicio = servicios[index];
          return ListTile(
            title: Text(servicio['nombre'] ?? ''),
            onTap: () {
              Navigator.pop(context, servicio);
            },
          );
        },
      ),
    );
  }
}
