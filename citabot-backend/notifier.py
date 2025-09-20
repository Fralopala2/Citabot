import os
import json
# Removed typing imports for compatibility

# Firebase es opcional - solo se inicializa si el archivo de credenciales existe
firebase_app = None
messaging = None

# Almacén de tokens de dispositivos registrados
registered_tokens = set()

try:
    if os.path.exists("firebase-service-account.json"):
        import firebase_admin
        from firebase_admin import credentials, messaging as fb_messaging
        
        # Inicializar Firebase con la cuenta de servicio
        cred = credentials.Certificate("firebase-service-account.json")
        firebase_app = firebase_admin.initialize_app(cred)
        messaging = fb_messaging
        print("Firebase initialized successfully")
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

def send_new_appointment_notification(estacion, fecha, hora):
    """Envía notificación específica para nueva cita disponible"""
    title = "🎉 Nueva cita disponible!"
    message = f"{estacion}\n📅 {fecha} a las {hora}"
    
    data = {
        "type": "new_appointment",
        "estacion": estacion,
        "fecha": fecha,
        "hora": hora
    }
    
    send_notification_to_all(title, message, data)

def get_registered_tokens_count():
    """Retorna el número de tokens registrados"""
    return len(registered_tokens)
