class Config {
  // Backend URL configuration
  static const bool isProduction =
      true; // Change to false for local development

  static const String _localUrl = 'http://10.0.2.2:8000';
  static const String _productionUrl =
      'https://citabot.onrender.com'; // Your actual Render URL

  static String get baseUrl => isProduction ? _productionUrl : _localUrl;

  // API endpoints
  static String get estacionesUrl => '$baseUrl/itv/estaciones';
  static String get serviciosUrl => '$baseUrl/itv/servicios';
  static String get fechasUrl => '$baseUrl/itv/fechas';
  static String get registerTokenUrl => '$baseUrl/register-token';
  
  // Installation tracking endpoints
  static String get trackInstallationUrl => '$baseUrl/track-installation';
  static String get trackUsageUrl => '$baseUrl/track-usage';
}
