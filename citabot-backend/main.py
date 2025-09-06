
from fastapi import FastAPI, Request, Query
from notifier import send_notification
from scraper_sitval import get_group_startup, extract_stations, get_next_dates_with_hours

app = FastAPI()


# Endpoint para registrar el token FCM
@app.post("/register-token")
async def register_token(request: Request):
    data = await request.json()
    token = data.get("token")
    # Aquí podrías guardar el token en una base de datos o archivo
    print(f"Token FCM recibido: {token}")
    return {"status": "token registrado"}


# Endpoint para obtener todas las estaciones reales
INSTANCE_CODE = "i4xmz7unei3sw70v2vuutgzh2m0f9v9z"
@app.get("/itv/estaciones")
def get_estaciones():
    data = get_group_startup(INSTANCE_CODE)
    stations = extract_stations(data)
    return {"estaciones": stations}

# Endpoint para obtener fechas y horas próximas de cita real
@app.get("/itv/fechas")
def get_fechas(store: int = Query(...), service: int = Query(...), n: int = Query(3)):
    fechas = get_next_dates_with_hours(store, service, INSTANCE_CODE, n)
    return {"fechas": fechas}
