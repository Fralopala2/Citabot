import os

# Firebase es opcional - solo se inicializa si el archivo de credenciales existe
firebase_app = None
messaging = None

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

def send_notification(message):
    """Envía notificación push si Firebase está configurado"""
    if not messaging or not firebase_app:
        print(f"Notification would be sent: {message} (Firebase not configured)")
        return
    
    # Token del dispositivo (puedes cargarlo desde .env si prefieres)
    device_token = "TU_DEVICE_TOKEN_AQUI"

    # Crear el mensaje
    notification = messaging.Message(
        notification=messaging.Notification(
            title="Cita Previa",
            body=message
        ),
        token=device_token
    )

    try:
        response = messaging.send(notification)
        print(f"Notification sent successfully: {response}")
    except Exception as e:
        print(f"Error sending notification: {e}")
