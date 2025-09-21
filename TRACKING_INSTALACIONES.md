# Sistema de Tracking de Instalaciones para Google Play

## ¿Qué hace este sistema?

Este sistema te permite rastrear exactamente qué testers tienen tu app instalada y cuáles la desinstalan. Esto es crucial para cumplir con el requisito de Google Play de tener **12 testers activos durante 14 días**.

## ¿Cómo funciona?

### 1. En la App (Flutter)
- Cuando un tester instala la app, automáticamente se genera un ID único usando Firebase Anonymous Auth
- La app envía datos de instalación al backend una sola vez
- Cada vez que el tester abre la app, se envía un "heartbeat" para confirmar que sigue activo

### 2. En el Backend (Python)
- **`/track-installation`**: Recibe datos cuando alguien instala la app
- **`/track-usage`**: Recibe datos cada vez que alguien usa la app  
- **`/admin/testers`**: Te muestra el estado de todos los testers

## ¿Qué información obtienes?

Al visitar `https://citabot.onrender.com/admin/testers` verás:

```json
{
  "total_testers": 15,
  "active_installations": 12,
  "testers": [
    {
      "user_id": "abcd1234efgh...",
      "platform": "android", 
      "app_version": "1.0.8",
      "install_date": "2024-09-21T10:00:00.000Z",
      "last_seen": "2024-09-21T15:30:00.000Z",
      "days_since_install": 0,
      "days_since_last_seen": 0
    }
  ]
}
```

## ¿Cómo identificar a cada tester?

### Opción 1: Usar Firebase UID (Recomendado)
- Cada tester tiene un ID único automático
- No necesitas hacer nada extra
- Puedes pedirles que te compartan su Firebase UID desde la app

### Opción 2: Mapear manualmente
- Anota qué tester instaló la app a qué hora
- Correlaciona con los datos de instalación por timestamp

## ¿Cómo detectar problemas?

### Tester que desinstaló la app:
- `days_since_last_seen` > 2 días → Probablemente desinstaló

### Tester activo:
- `days_since_last_seen` <= 1 día → App instalada y en uso

### Necesitas más testers si:
- `active_installations` < 12

## Configuración de Firebase

Para que funcione completamente necesitas:

1. **Habilitar Firebase Anonymous Auth:**
   - Ve a Firebase Console → Authentication → Sign-in method
   - Habilita "Anonymous"

2. **Verificar google-services.json:**
   - Asegúrate de que el archivo esté en `android/app/`
   - Debe coincidir con tu proyecto Firebase

## URLs importantes

- **Ver testers**: `https://citabot.onrender.com/admin/testers`
- **Health check**: `https://citabot.onrender.com/health`

## Notas importantes

- Los datos se almacenan temporalmente en memoria del servidor
- Si el servidor se reinicia, los datos se pierden (normal en Render free tier)
- Para producción, considera usar una base de datos persistente
- Firebase Anonymous Auth funciona sin login del usuario

## Próximos pasos

1. **Asegúrate de que Firebase Anonymous Auth esté habilitado**
2. **Distribuye la v1.0.8+9 a tus testers**
3. **Monitorea diariamente**: `https://citabot.onrender.com/admin/testers`
4. **Lleva registro manual** de qué tester es cada UID (al menos los primeros días)

¡Con esto deberías poder cumplir el requisito de Google Play! 🎉