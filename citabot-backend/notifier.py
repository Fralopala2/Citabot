import os
import json
# Removed typing imports for compatibility

# Firebase es opcional - solo se inicializa si el archivo de credenciales existe
firebase_app = None
messaging = None

# Almacén de tokens de dispositivos registrados
registered_tokens = set()

try:
    # Try to initialize Firebase using FIREBASE_CONFIG environment variable (JSON string)
    firebase_config_json = os.getenv("FIREBASE_CONFIG")
    
    if firebase_config_json:
        import firebase_admin
        from firebase_admin import credentials, messaging as fb_messaging
        
        # Parse JSON from environment variable
        firebase_config = json.loads(firebase_config_json)
        cred = credentials.Certificate(firebase_config)
        firebase_app = firebase_admin.initialize_app(cred)
        messaging = fb_messaging
        print("Firebase initialized successfully from FIREBASE_CONFIG environment variable")
    elif os.path.exists("firebase-service-account.json"):
        import firebase_admin
        from firebase_admin import credentials, messaging as fb_messaging
        
        # Fallback: usar archivo JSON local
        cred = credentials.Certificate("firebase-service-account.json")
        firebase_app = firebase_admin.initialize_app(cred)
        messaging = fb_messaging
        print("Firebase initialized successfully from JSON file")
    else:
        print("Firebase service account not found - notifications disabled")
except Exception as e:
    print(f"Firebase initialization failed: {e}")

def register_device_token(token):
    """Registra un token de dispositivo para notificaciones"""
    if token and len(token) > 10:  # Validación básica
        registered_tokens.add(token)
        print(f"Device token registered: {token[:20]}...")
        return True
    return False

def send_notification_to_all(title, message, data=None):
    """Envía notificación push a todos los dispositivos registrados"""
    if not messaging or not firebase_app or not registered_tokens:
        print(f"Notification would be sent to {len(registered_tokens)} devices: {title} - {message}")
        return
    
    successful_sends = 0
    failed_tokens = []
    
    for token in registered_tokens.copy():  # Usar copia para poder modificar durante iteración
        try:
            # Crear el mensaje
            notification_msg = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=message
                ),
                data=data or {},
                token=token
            )
            
            response = messaging.send(notification_msg)
            successful_sends += 1
            print(f"Notification sent successfully to {token[:20]}...: {response}")
            
        except Exception as e:
            print(f"Error sending notification to {token[:20]}...: {e}")
            # Si el token es inválido, lo removemos
            if "invalid" in str(e).lower() or "not-registered" in str(e).lower():
                failed_tokens.append(token)
    
    # Remover tokens inválidos
    for token in failed_tokens:
        registered_tokens.discard(token)
        print(f"Removed invalid token: {token[:20]}...")
    
    print(f"Notifications sent: {successful_sends}/{len(registered_tokens) + len(failed_tokens)}")

def send_new_appointment_notification(estacion, fecha, hora, specific_token=None):
    """Envía notificación específica para nueva cita disponible"""
    title = "🎉 Nueva cita disponible!"
    message = f"{estacion}\n📅 {fecha} a las {hora}"
    
    data = {
        "type": "new_appointment",
        "estacion": estacion,
        "fecha": fecha,
        "hora": hora
    }
    
    if specific_token:
        send_notification_to_token(title, message, data, specific_token)
    else:
        send_notification_to_all(title, message, data)

def send_notification_to_token(title, message, data, token):
    """Envía notificación push a un token específico"""
    if not messaging or not firebase_app:
        print(f"Test notification would be sent to {token[:20]}...: {title} - {message}")
        return True
    
    try:
        # Crear el mensaje
        notification_msg = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message
            ),
            data=data or {},
            token=token
        )
        
        response = messaging.send(notification_msg)
        print(f"Test notification sent successfully to {token[:20]}...: {response}")
        return True
        
    except Exception as e:
        print(f"Error sending test notification to {token[:20]}...: {e}")
        return False

def get_registered_tokens_count():
    """Retorna el número de tokens registrados"""
    return len(registered_tokens)

def unregister_device_token(token):
    """Desregistra un token específico"""
    if token in registered_tokens:
        registered_tokens.remove(token)
        print(f"Device token unregistered: {token[:20]}...")
        return True
    else:
        print(f"Token not found for unregistration: {token[:20]}...")
        return False

def clear_all_tokens():
    """Borra todos los tokens registrados"""
    count = len(registered_tokens)
    registered_tokens.clear()
    print(f"Cleared {count} registered tokens")
    return count

def get_all_tokens():
    """Retorna una lista de todos los tokens (para debugging)"""
    return list(registered_tokens)

def is_firebase_enabled():
    """Retorna True si Firebase está configurado y disponible"""
    return messaging is not None and firebase_app is not None
