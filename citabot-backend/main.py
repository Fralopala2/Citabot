import threading
import time
from fastapi import FastAPI, Request, Query
from notifier import send_notification
from scraper_sitval import SitValScraper



scraper = SitValScraper()
app = FastAPI()

# In-memory cache for available slots
slots_cache = {}
slots_cache_lock = threading.Lock()
CACHE_TTL = 300  # seconds (5 minutes)

def cache_key(store, service):
    return f"{store}:{service}"

def get_cached_slots(store, service):
    key = cache_key(store, service)
    with slots_cache_lock:
        entry = slots_cache.get(key)
        if entry and (time.time() - entry['timestamp'] < CACHE_TTL):
            return entry['data']
    return None

def set_cached_slots(store, service, data):
    key = cache_key(store, service)
    with slots_cache_lock:
        slots_cache[key] = {'data': data, 'timestamp': time.time()}

# Background thread to refresh cache periodically
def background_cache_refresher():
    while True:
        # You can customize which stations/services to refresh
        # For demo: refresh all keys already in cache
        with slots_cache_lock:
            keys = list(slots_cache.keys())
        for key in keys:
            store, service = key.split(":")
            instance_code = scraper.get_instance_code_robust()
            data = scraper.get_next_available_slots(store, service, instance_code, 10)
            set_cached_slots(store, service, data)
        time.sleep(CACHE_TTL)

threading.Thread(target=background_cache_refresher, daemon=True).start()

# Endpoint para obtener servicios disponibles según estación
@app.get("/itv/servicios")
def get_servicios(store_id: str):
    instance_code = scraper.get_instance_code_robust()
    group_data = scraper.get_group_startup(instance_code, store_id)
    servicios = []
    # Buscar la estación por store_id y devolver servicios simulados según tipo
    for prov in group_data.get('groups', {}).values():
        for level2 in prov.get('level2', {}).values():
            for store in level2.get('stores', {}).values():
                if str(store.get('store')) == str(store_id):
                    tipo = level2.get('name')
                    if tipo == 'Estaciones fijas':
                        servicios = [
                            {'nombre': 'Turismo', 'service': 259},
                            {'nombre': 'Motocicleta', 'service': 260},
                            {'nombre': 'Vehículo ligero', 'service': 261},
                            {'nombre': 'Ciclomotor/ Motocicleta sin catalizar', 'service': 262},
                        ]
                    elif tipo == 'Estaciones móviles':
                        servicios = [
                            {'nombre': 'Turismo', 'service': 259},
                            {'nombre': 'Motocicleta', 'service': 260},
                        ]
                    elif tipo == 'Estaciones agrícolas':
                        servicios = [
                            {'nombre': 'Vehículo agrícola', 'service': 263},
                        ]
                    else:
                        servicios = [
                            {'nombre': 'Turismo', 'service': 259},
                        ]
                    return {"servicios": servicios}
    return {"servicios": []}




# Endpoint para registrar el token FCM
@app.post("/register-token")
async def register_token(request: Request):
    data = await request.json()
    token = data.get("token")
    # Aquí podrías guardar el token en una base de datos o archivo
    print(f"Token FCM recibido: {token}")
    return {"status": "token registrado"}


# Endpoint para obtener todas las estaciones reales
INSTANCE_CODE = "qwkwr0is9qcmuwdg7e3x1pvqepc5e0p9"
@app.get("/itv/estaciones")
def get_estaciones():
    print("DEBUG: INICIO get_estaciones")
    instance_code = scraper.get_instance_code_robust()
    print(f"DEBUG: instance_code obtenido: {instance_code}")
    group_data = scraper.get_group_startup(instance_code)
    print(f"DEBUG: group_data obtenido: {group_data}")
    estaciones = scraper.extract_stations(group_data)
    print(f"DEBUG: estaciones extraidas: {estaciones}")
    print("DEBUG: Entrando en get_estaciones")
    print("DEBUG: Antes de llamar a scraper.get_group_startup")
    # Devuelve la lista de servicios y parámetros de la estación
    # Obtener instanceCode dinámico
    # El instanceCode debe ser gestionado por el frontend/cliente y propagado en cada consulta
    # Para mostrar todas las estaciones, usamos un instanceCode fijo o '0'
    instance_code = scraper.get_instance_code_robust()
    group_data = scraper.get_group_startup(instance_code)
    estaciones = scraper.extract_stations(group_data)
    return {"servicios": estaciones}


# Endpoint para obtener fechas y horas próximas de cita real (con caché)
@app.get("/itv/fechas")
def get_fechas(store: str, service: str, instance_code: str = "0", n: int = 3):
    # Try cache first
    cached = get_cached_slots(store, service)
    if cached:
        return {"fechas_horas": cached[:n]}
    # If not cached, fetch and cache
    fechas_horas = scraper.get_next_available_slots(store, service, instance_code, n)
    set_cached_slots(store, service, fechas_horas)
    return {"fechas_horas": fechas_horas}
