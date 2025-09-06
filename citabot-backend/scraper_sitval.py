# Obtiene el sessionId necesario para reservar una hora
def get_session_id(store, service, instance_code, date):
    # Normalmente el sessionId se obtiene tras seleccionar día/hora en la web
    # Aquí solo se simula el flujo, en la web se genera tras varios pasos
    # Si la API lo devuelve en algún endpoint, habría que capturarlo
    # Por ahora, devolver None y mostrar advertencia
    return None

# Simula la validación de descuento y reserva de hora
def set_discount_followup(store, sessionid, service, dateSel):
    url = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=set-discount-followup"
    payload = {
        "store": str(store),
        "sessionId": sessionid,
        "service": str(service),
        "dateSel": dateSel
    }
    response = requests.post(url, data=payload)
    return response.json()

# Consulta el precio real de la cita
def get_real_price(store, service, date, sessionid):
    url = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=get-real-price"
    payload = {
        "store": str(store),
        "service": str(service),
        "date": date,
        "sessionId": sessionid
    }
    response = requests.post(url, data=payload)
    return response.json()
# Consulta las horas libres para un día concreto
def get_service_day_data(store, service, instance_code, date, itinerary_place="0"):
    url = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=serviceDayData"
    payload = {
        "store": str(store),
        "service": str(service),
        "instanceCode": instance_code,
        "date": date,
        "itineraryPlace": itinerary_place,
        "dateHour": date
    }
    response = requests.post(url, data=payload)
    return response.json()
# Extrae todas las estaciones de la estructura devuelta por groupStartup
def extract_stations(data):
    stations = []
    for prov_key, prov in data.get('groups', {}).items():
        provincia = prov.get('name')
        # Estaciones fijas, móviles, agrícolas
        for level2 in prov.get('level2', {}).values():
            tipo = level2.get('name')
            for store in level2.get('stores', {}).values():
                station = {
                    'provincia': provincia,
                    'tipo': tipo,
                    'nombre': store.get('name'),
                    'store_id': store.get('store'),
                    'direccion': store.get('short_description', ''),
                    'primer_dia': store.get('first_availability', None)
                }
                stations.append(station)
    return stations


# Obtiene las fechas y horas más próximas para una estación y tipo de vehículo
def get_next_dates_with_hours(store, service, instance_code, n=3):
    import datetime
    today = datetime.date.today()
    fechas_horas = []
    # Buscar fechas en los próximos 2 meses
    for month_offset in range(2):
        date = (today.replace(day=1) + datetime.timedelta(days=32*month_offset)).replace(day=1)
        cita_data = get_service_month_data(store, service, instance_code, date.strftime('%Y-%m-%d'))
        open_days = cita_data.get('get_open_days', [])
        for dia in sorted(open_days):
            horas_data = get_service_day_data(store, service, instance_code, dia)
            horas_libres = horas_data.get('get_open_hours', [])
            for hora in horas_libres:
                # Simular obtención de sessionId (en la web se genera tras seleccionar hora)
                sessionid = get_session_id(store, service, instance_code, dia)
                # Validar descuento y precio si sessionid estuviera disponible
                # discount_info = set_discount_followup(store, sessionid, service, f"{dia} {hora}") if sessionid else None
                # price_info = get_real_price(store, service, f"{dia} {hora}", sessionid) if sessionid else None
                fechas_horas.append({
                    "fecha": dia,
                    "hora": hora,
                    "sessionid": sessionid,
                    # "discount_info": discount_info,
                    # "price_info": price_info
                })
                if len(fechas_horas) >= n:
                    return fechas_horas
        if len(fechas_horas) >= n:
            break
    return fechas_horas
import requests
from bs4 import BeautifulSoup

# Paso 1: Obtener las provincias disponibles


# Obtiene provincias, estaciones y fechas desde el endpoint AJAX
def get_group_startup(instance_code):
    url = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=groupStartup"
    payload = {
        "store": "1",
        "owner": "1",
        "instanceCode": instance_code,
        "group": "4"
    }
    response = requests.post(url, data=payload)
    return response.json()

# Obtiene disponibilidad y precio para una estación y servicio
def get_service_month_data(store, service, instance_code, date="2025-09-01"):
    url = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=serviceMonthData"
    payload = {
        "store": str(store),
        "itineraryPlace": "0",
        "instanceCode": instance_code,
        "firstCall": "true",
        "date": date,
        "service": str(service)
    }
    response = requests.post(url, data=payload)
    return response.json()


# Ejemplo de uso

if __name__ == "__main__":
    instance_code = "i4xmz7unei3sw70v2vuutgzh2m0f9v9z"
    # 1. Obtener estructura
    data = get_group_startup(instance_code)
    stations = extract_stations(data)
    print("Estaciones disponibles:")
    for s in stations:
        print(s)

    # 2. Simular selección de estación y tipo de vehículo
    # Ejemplo: Gandia (store 17), Turismo (service 259)
    store = 17
    service = 259
    fechas = get_next_dates_with_hours(store, service, instance_code, n=3)
    print(f"Fechas más próximas para estación {store} y servicio {service}:")
    print(fechas)
