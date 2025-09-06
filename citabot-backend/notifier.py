import requests

def send_notification(message):
    # Replace with your Firebase server key and device token
    server_key = "YOUR_FIREBASE_SERVER_KEY"
    device_token = "YOUR_DEVICE_TOKEN"

    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "to": device_token,
        "notification": {
            "title": "Cita Previa",
            "body": message
        }
    }

    requests.post("https://fcm.googleapis.com/fcm/send", headers=headers, json=payload)
