import os
import json

# Firebase es opcional - solo se inicializa si el archivo de credenciales existe
firebase_app = None
messaging = None

# Almacén robusto de tokens: token -> {"user_id": ..., "favoritos": [...]}
TOKENS_DATA_FILE = "tokens_data.json"
registered_tokens = {}  # token -> {"user_id":..., "favoritos": [...]}

def load_tokens_data():
    global registered_tokens
    try:
        if os.path.exists(TOKENS_DATA_FILE):
            with open(TOKENS_DATA_FILE, 'r', encoding='utf-8') as f:
                registered_tokens = json.load(f)
                print(f"📂 Loaded {len(registered_tokens)} tokens from persistent storage")
        else:
            registered_tokens = {}
    except Exception as e:
        print(f"❌ Error loading tokens data: {e}")
        registered_tokens = {}

def save_tokens_data():
    try:
        with open(TOKENS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(registered_tokens, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(registered_tokens)} tokens to persistent storage")
        return True
    except Exception as e:
        print(f"❌ Error saving tokens data: {e}")
        return False

# Cargar tokens al iniciar
load_tokens_data()

try:
    firebase_config_json = os.getenv("FIREBASE_CONFIG")
    if firebase_config_json:
        import firebase_admin
        from firebase_admin import credentials, messaging as fb_messaging
        firebase_config = json.loads(firebase_config_json)
        cred = credentials.Certificate(firebase_config)
        firebase_app = firebase_admin.initialize_app(cred)
        messaging = fb_messaging
        print("Firebase initialized successfully from FIREBASE_CONFIG environment variable")
    elif os.path.exists("firebase-service-account.json"):
        import firebase_admin
        from firebase_admin import credentials, messaging as fb_messaging
        cred = credentials.Certificate("firebase-service-account.json")
        firebase_app = firebase_admin.initialize_app(cred)
        messaging = fb_messaging
        print("Firebase initialized successfully from JSON file")
    else:
        print("Firebase service account not found - notifications disabled")
except Exception as e:
    print(f"Firebase initialization failed: {e}")

def register_device_token(token, user_id=None, favoritos=None):
    """
    Registra o actualiza un token de dispositivo con user_id y favoritos.
    Si el token ya existe, actualiza user_id y favoritos.
    """
    if token and len(token) > 10:
        if token not in registered_tokens:
            registered_tokens[token] = {}
        if user_id:
            registered_tokens[token]["user_id"] = user_id
        if favoritos is not None:
            registered_tokens[token]["favoritos"] = favoritos
        save_tokens_data()
        print(f"Device token registered: {token[:20]}... user_id={user_id} favoritos={favoritos}")
        return True
    return False

def send_notification_to_all(title, message, data=None):
    """
    Envía notificación push a todos los dispositivos registrados (legacy, no filtra).
    Usar solo para pruebas o casos especiales.
    """
    if not messaging or not firebase_app or not registered_tokens:
        print(f"Notification would be sent to {len(registered_tokens)} devices: {title} - {message}")
        return
    successful_sends = 0
    failed_tokens = []
    for token in list(registered_tokens.keys()):
        try:
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
            if "invalid" in str(e).lower() or "not-registered" in str(e).lower():
                failed_tokens.append(token)
    for token in failed_tokens:
        registered_tokens.pop(token, None)
        print(f"Removed invalid token: {token[:20]}...")
    save_tokens_data()
    print(f"Notifications sent: {successful_sends}/{len(registered_tokens) + len(failed_tokens)}")

def send_notification_to_favorites(title, message, data, estacion):
    """
    Envía notificación solo a usuarios con la estación en favoritos.
    Solo los tokens cuyo array de favoritos contiene la estación recibirán la notificación.
    """
    if not messaging or not firebase_app or not registered_tokens:
        print(f"Notification would be sent to {len(registered_tokens)} devices: {title} - {message}")
        return
    successful_sends = 0
    failed_tokens = []
    for token, info in list(registered_tokens.items()):
        favoritos = info.get("favoritos", [])
        if estacion in favoritos:
            try:
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
                if "invalid" in str(e).lower() or "not-registered" in str(e).lower():
                    failed_tokens.append(token)
    for token in failed_tokens:
        registered_tokens.pop(token, None)
        print(f"Removed invalid token: {token[:20]}...")
    save_tokens_data()
    print(f"Notifications sent to favorites: {successful_sends}")

def send_new_appointment_notification(estacion, fecha, hora, specific_token=None):
    """
    Envía notificación específica para nueva cita disponible.
    Si specific_token está presente, solo se envía a ese token.
    Si no, se filtra por favoritos usando send_notification_to_favorites.
    """
    title = "🎉 Nueva cita disponible!"
    message = f"{estacion}\\n📅 {fecha} a las {hora}"
    data = {
        "type": "new_appointment",
        "estacion": estacion,
        "fecha": fecha,
        "hora": hora
    }
    if specific_token:
        send_notification_to_token(title, message, data, specific_token)
    else:
        send_notification_to_favorites(title, message, data, estacion)

def send_notification_to_token(title, message, data, token):
    """Envía notificación push a un token específico"""
    if not messaging or not firebase_app:
        print(f"Test notification would be sent to {token[:20]}...: {title} - {message}")
        return True
    try:
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
    """Retorna el número de tokens registrados (únicos)"""
    return len(registered_tokens)

def unregister_device_token(token):
    """Desregistra un token específico y lo elimina del almacenamiento persistente"""
    if token in registered_tokens:
        registered_tokens.pop(token)
        save_tokens_data()
        print(f"Device token unregistered: {token[:20]}...")
        return True
    else:
        print(f"Token not found for unregistration: {token[:20]}...")
        return False

def clear_all_tokens():
    """Borra todos los tokens registrados y limpia el almacenamiento persistente"""
    count = len(registered_tokens)
    registered_tokens.clear()
    save_tokens_data()
    print(f"Cleared {count} registered tokens")
    return count

def get_all_tokens():
    """Retorna una lista de todos los tokens registrados (para debugging)"""
    return list(registered_tokens.keys())

def is_firebase_enabled():
    """Retorna True si Firebase está configurado y disponible"""
    return messaging is not None and firebase_app is not None