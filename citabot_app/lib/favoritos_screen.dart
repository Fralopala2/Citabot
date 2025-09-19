import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class FavoritosScreen extends StatefulWidget {
  final List<dynamic> estaciones;
  const FavoritosScreen({super.key, required this.estaciones});

  @override
  State<FavoritosScreen> createState() => _FavoritosScreenState();
}

class _FavoritosScreenState extends State<FavoritosScreen> {
  Set<String> favoritos = {};

  @override
  void initState() {
    super.initState();
    _loadFavoritos();
  }

  Future<void> _loadFavoritos() async {
    final prefs = await SharedPreferences.getInstance();
    final favs = prefs.getStringList('favoritos') ?? [];
    setState(() {
      favoritos = favs.toSet();
    });
  }

  Future<void> _saveFavoritos() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('favoritos', favoritos.toList());
  }

  void _toggleFavorito(String id) {
    setState(() {
      if (favoritos.contains(id)) {
        favoritos.remove(id);
      } else {
        favoritos.add(id);
      }
    });
    _saveFavoritos();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Estaciones Favoritas'),
        backgroundColor: Colors.deepPurple,
        iconTheme: const IconThemeData(color: Colors.white),
        titleTextStyle: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w500),
      ),
      body: ListView.builder(
        itemCount: widget.estaciones.length,
        itemBuilder: (context, index) {
          final estacion = widget.estaciones[index];
          final id = estacion['store_id'].toString();
          final nombre = '${estacion['provincia'] ?? ''} - ${estacion['nombre'] ?? ''} (${estacion['tipo'] ?? ''})';
          final selected = favoritos.contains(id);
          return ListTile(
            title: Text(nombre),
            trailing: Icon(
              selected ? Icons.favorite : Icons.favorite_border,
              color: selected ? Colors.red : null,
            ),
            onTap: () => _toggleFavorito(id),
          );
        },
      ),
    );
  }
}
