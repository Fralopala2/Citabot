


from fastapi import FastAPI, Request, Query
from notifier import send_notification
from scraper_sitval import SitValScraper



scraper = SitValScraper()
app = FastAPI()

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
INSTANCE_CODE = "i4xmz7unei3sw70v2vuutgzh2m0f9v9z"
@app.get("/itv/estaciones")
def get_estaciones():
    # Devuelve la lista de servicios y parámetros de la estación
    # Obtener instanceCode dinámico
    # El instanceCode debe ser gestionado por el frontend/cliente y propagado en cada consulta
    # Para mostrar todas las estaciones, usamos un instanceCode fijo o '0'
    instance_code = scraper.get_instance_code_robust()
    group_data = scraper.get_group_startup(instance_code)
    estaciones = scraper.extract_stations(group_data)
    return {"servicios": estaciones}

# Endpoint para obtener fechas y horas próximas de cita real
@app.get("/itv/fechas")
def get_fechas(store: str, service: str, instance_code: str = "0", n: int = 3):
    # El instanceCode debe ser el mismo que se usó para consultar groupStartup y servicios
    fechas_horas = scraper.get_next_available_slots(store, service, instance_code, n)
    return {"fechas_horas": fechas_horas}
