from fastapi import FastAPI
from scraper import check_availability
from notifier import send_notification

app = FastAPI()

@app.get("/check")
def check_cita():
    available = check_availability()
    if available:
        send_notification("Appointment available!")
        return {"status": "available"}
    return {"status": "not available"}
