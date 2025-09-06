import firebase_admin
from firebase_admin import credentials, messaging

# Inicializar Firebase con la cuenta de servicio
cred = credentials.Certificate("firebase-service-account.json")
firebase_admin.initialize_app(cred)

def send_notification(message):
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
