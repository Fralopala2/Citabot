

# Este código se usa para pruebas cuando no se puede obtener uno dinámico
INSTANCE_CODE_TEMPORAL = "2g8mkjxs7t6sk5gawgri5x1u2nryqcxb"

# Devuelve la disponibilidad y el precio para una estación y tipo de servicio
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
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception:
        return {}

# Devuelve los horarios disponibles para un día específico en una estación y servicio
def get_service_day_data(store, service, instance_code, dia):
    url = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=serviceDayData"
    payload = {
        "store": str(store),
        "service": str(service),
        "instanceCode": instance_code,
        "date": dia,
        "itineraryPlace": "0",
        "dateHour": dia
    }
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception:
        return {}

# Prueba temporal para mostrar fechas y horas libres usando parámetros fijos
if __name__ == "__main__":
    print("=== Prueba temporal de fechas y horas libres ===")
    store = "21"
    service = "323"  # Este servicio sí tiene disponibilidad real según pruebas previas
    instance_code = INSTANCE_CODE_TEMPORAL
    import datetime
    today = datetime.date.today()
    # Se consultan dos meses para obtener más opciones de fechas
    for month_offset in range(2):
        date = (today.replace(day=1) + datetime.timedelta(days=32*month_offset)).replace(day=1)
        cita_data = get_service_month_data(store, service, instance_code, date.strftime('%Y-%m-%d'))
        print(f"Respuesta serviceMonthData para store={store}, service={service}, date={date.strftime('%Y-%m-%d')}: {cita_data}")
        open_days = cita_data.get('get_open_days', {})
        if not open_days:
            print("No hay días libres en este mes.")
            continue
    # Filtra los días que realmente son fechas disponibles (descarta claves tipo 'n0', 'n1')
        if isinstance(open_days, dict):
            dias_iter = [v for v in open_days.values() if isinstance(v, str) and not v.startswith('n')]
        elif isinstance(open_days, list):
            dias_iter = [v for v in open_days if isinstance(v, str) and not v.startswith('n')]
        for dia in dias_iter:
            print(f"Día libre: {dia}")
            horas_data = get_service_day_data(store, service, instance_code, dia)
            print(f"Horarios disponibles para el día {dia}: {horas_data}")
# InstanceCode temporal para pruebas
INSTANCE_CODE_TEMPORAL = "2g8mkjxs7t6sk5gawgri5x1u2nryqcxb"
# --- Funciones stub/faltantes ---
def check_system_status():
    # TODO: Implementar chequeo real del sistema
    # Por ahora, siempre retorna True (sin incidencias)
    return True

def get_instance_code_from_startup_response():
    # TODO: Implementar extracción real desde respuesta startup
    return None


# --- Métodos robustos para obtener instanceCode ---
def find_instance_code_recursive(obj, path=""):
    """Busca recursivamente instanceCode en estructura JSON"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'instanceCode' and value and len(str(value)) >= 25:
                return str(value)
            if isinstance(value, (dict, list)):
                result = find_instance_code_recursive(value, f"{path}.{key}")
                if result:
                    return result
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            result = find_instance_code_recursive(item, f"{path}[{i}]")
            if result:
                return result
    return None

def get_dynamic_instance_code():
    """Extrae el instanceCode dinámico siguiendo el flujo real del navegador"""
    import requests
    import re
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://citaitvsitval.com',
        'Referer': 'https://citaitvsitval.com/',
        'Connection': 'keep-alive'
    })
    try:
        session.get("https://citaitvsitval.com/", timeout=10)
        startup_payload = {'store': '1', 'itineraryPlace': '0', 'instanceCode': ''}
        startup_response = session.post(
            'https://citaitvsitval.com/ajax/ajaxmodules.php?module=startUp',
            data=startup_payload
        )
        group_payload = {'store': '1', 'owner': '1', 'instanceCode': '', 'group': '4'}
        group_response = session.post(
            'https://citaitvsitval.com/ajax/ajaxmodules.php?module=groupStartup', 
            data=group_payload
        )
        # Check cookies
        for cookie in session.cookies:
            cookie_value = cookie.value
            if len(cookie_value) >= 25 and re.match(r'^[a-z0-9]+$', cookie_value):
                return cookie_value
        # Check JSON response
        try:
            group_data = group_response.json()
            instance_code = find_instance_code_recursive(group_data)
            if instance_code:
                return instance_code
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"Error en get_dynamic_instance_code: {e}")
        return None

def get_instance_code_robust():
    print("=== Extrayendo instanceCode dinámico ===")
    # Usar el temporal si está definido
    if INSTANCE_CODE_TEMPORAL:
        print(f"Usando instanceCode temporal: {INSTANCE_CODE_TEMPORAL}")
        return INSTANCE_CODE_TEMPORAL
    instance_code = get_dynamic_instance_code()
    if instance_code and len(instance_code) >= 25:
        print(f"✓ InstanceCode obtenido: {instance_code}")
        return instance_code
    # Fallback: HTML scraping
    code = get_instance_code_from_web()
    return code if code else "SISTEMA_CON_INCIDENCIAS"

def get_service_day_data(store, service_id, instance_code_dynamic, dia):
    # TODO: Implementar consulta real a serviceDayData
    # Retorna estructura vacía para evitar errores
    return {'get_day_slots': {}, 'get-hour-prices': '{}'}

def get_session_id(store, service_id, instance_code_dynamic, dia):
    # TODO: Implementar obtención real de sessionid
    return None

def set_discount_followup(store, sessionid, service_id, fecha_hora):
    # TODO: Implementar lógica real de descuento
    return None

import re
import json


def get_instance_code_from_web():
    url = "https://citaitvsitval.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        print("Obteniendo página principal...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
        print(f"HTML obtenido: {len(html_content)} caracteres")
        soup = BeautifulSoup(html_content, 'html.parser')
        patterns = [
            r'instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'instance_code["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'["\']instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'instanceCode:\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'var\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'let\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'const\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
            r'["\']([a-zA-Z0-9]{25,35})["\']',
        ]
        scripts = soup.find_all('script')
        print(f"Encontrados {len(scripts)} scripts")
        for i, script in enumerate(scripts):
            if script.string:
                content = script.string
                print(f"Script {i}: {len(content)} caracteres")
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if len(match) >= 20:
                            print(f"Posible instanceCode encontrado con patrón '{pattern}': {match}")
                            if re.match(r'^[a-zA-Z0-9]{20,35}$', match):
                                return match
        print("Buscando en atributos DOM...")
        for attr_name in ['data-instance-code', 'data-instancecode', 'instancecode', 'instance-code']:
            elements = soup.find_all(attrs={attr_name: True})
            for element in elements:
                value = element.get(attr_name)
                if value and len(value) >= 20:
                    print(f"InstanceCode encontrado en atributo {attr_name}: {value}")
                    return value
        print("Buscando en inputs hidden...")
        inputs = soup.find_all('input', {'type': 'hidden'})
        for input_elem in inputs:
            name = input_elem.get('name', '').lower()
            value = input_elem.get('value', '')
            if 'instance' in name and len(value) >= 20:
                print(f"InstanceCode encontrado en input hidden: {value}")
                return value
        print("Búsqueda general en HTML...")
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if len(match) >= 20 and re.match(r'^[a-zA-Z0-9]{20,35}$', match):
                    print(f"InstanceCode encontrado en HTML general: {match}")
                    return match
        print("No se encontró instanceCode en el HTML")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None
        import json

        def get_instance_code_from_web():
            url = "https://citaitvsitval.com/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            try:
                print("Obteniendo página principal...")
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                html_content = response.text
                print(f"HTML obtenido: {len(html_content)} caracteres")
                soup = BeautifulSoup(html_content, 'html.parser')
                patterns = [
                    r'instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'instance_code["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'["\']instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'instanceCode:\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'var\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'let\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'const\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
                    r'["\']([a-zA-Z0-9]{25,35})["\']',
                ]
                scripts = soup.find_all('script')
                print(f"Encontrados {len(scripts)} scripts")
                for i, script in enumerate(scripts):
                    if script.string:
                        content = script.string
                        print(f"Script {i}: {len(content)} caracteres")
                        for pattern in patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                if len(match) >= 20:
                                    print(f"Posible instanceCode encontrado con patrón '{pattern}': {match}")
                                    if re.match(r'^[a-zA-Z0-9]{20,35}$', match):
                                        return match
                print("Buscando en atributos DOM...")
                for attr_name in ['data-instance-code', 'data-instancecode', 'instancecode', 'instance-code']:
                    elements = soup.find_all(attrs={attr_name: True})
                    for element in elements:
                        value = element.get(attr_name)
                        if value and len(value) >= 20:
                            print(f"InstanceCode encontrado en atributo {attr_name}: {value}")
                            return value
                print("Buscando en inputs hidden...")
                inputs = soup.find_all('input', {'type': 'hidden'})
                for input_elem in inputs:
                    name = input_elem.get('name', '').lower()
                    value = input_elem.get('value', '')
                    if 'instance' in name and len(value) >= 20:
                        print(f"InstanceCode encontrado en input hidden: {value}")
                        return value
                print("Búsqueda general en HTML...")
                for pattern in patterns:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    for match in matches:
                        if len(match) >= 20 and re.match(r'^[a-zA-Z0-9]{20,35}$', match):
                            print(f"InstanceCode encontrado en HTML general: {match}")
                            return match
                print("No se encontró instanceCode en el HTML")
                return None
            except requests.RequestException as e:
                print(f"Error en petición HTTP: {e}")
                return None
            except Exception as e:
                print(f"Error inesperado: {e}")
                return None
    # ...código mejorado del usuario...
    if not check_system_status():
        print("❌ Sistema no disponible por incidencias")
        return "SISTEMA_CON_INCIDENCIAS"
    print("=== Método 1: Scraping HTML ===")
    instance_code = get_instance_code_from_web()
    if instance_code:
        print(f"✓ InstanceCode obtenido por scraping: {instance_code}")
        return instance_code
    print("=== Método 2: Headers y cookies ===")
    instance_code = get_instance_code_from_startup_response()
    if instance_code:
        print(f"✓ InstanceCode obtenido de headers/cookies: {instance_code}")
        return instance_code
    print("=== Método 3: Petición directa ===")
    instance_code = get_instance_code_alternative()
    if instance_code:
        print(f"✓ InstanceCode obtenido por petición: {instance_code}")
        return instance_code
    print("=== Método 4: Trabajar sin instanceCode ===")
    print("ℹ️  Intentando funcionar sin instanceCode explícito")
    return ""  # String vacío para indicar que se puede trabajar sin él
def extract_stations(group_startup_data):
    estaciones = []
    if not group_startup_data:
        return estaciones
    for prov_key, prov in group_startup_data.get('groups', {}).items():
        provincia = prov.get('name')
        for level2 in prov.get('level2', {}).values():
            tipo = level2.get('name')
            for store in level2.get('stores', {}).values():
                estacion = {
                    'provincia': provincia,
                    'tipo': tipo,
                    'nombre': store.get('name'),
                    'store_id': store.get('store'),
                    'direccion': store.get('short_description', ''),
                    'primer_dia': store.get('first_availability', None)
                }
                if 'instanceCode' in store:
                    estacion['instanceCode'] = store['instanceCode']
                estaciones.append(estacion)
    return estaciones


# Obtiene las fechas y horas más próximas para una estación y tipo de vehículo
def get_next_dates_with_hours(store, service, instance_code, n=3):
    print(f"Buscando fechas para store={store}, service={service}, instance_code={instance_code}")
    import datetime
    today = datetime.date.today()
    fechas_horas = []
    # Usar el instanceCode recibido directamente
    service_id = service
    if not service_id:
        print(f"No se recibió el id del servicio para store={store}")
        return []
    service_price = None
    # Si no se recibe instanceCode, intentar obtenerlo de la web
    instance_code_actual = instance_code
    if not instance_code_actual or instance_code_actual == "0":
        print("No se recibió instanceCode válido, intentando obtenerlo de la web y otros métodos...")
        instance_code_actual = get_instance_code_robust()
        print(f"InstanceCode obtenido: {instance_code_actual}")
        if instance_code_actual == "SISTEMA_CON_INCIDENCIAS":
            print("No se puede continuar por incidencias en el sistema.")
            return []
    else:
        print(f"Usando instanceCode recibido: {instance_code_actual}")
    for month_offset in range(2):
        date = (today.replace(day=1) + datetime.timedelta(days=32*month_offset)).replace(day=1)
        cita_data = get_service_month_data(store, service_id, instance_code_actual, date.strftime('%Y-%m-%d'))
        print(f"Respuesta completa serviceMonthData para store={store}, service={service_id}, date={date.strftime('%Y-%m-%d')}: {cita_data}")
        if service_price is None:
            service_price = cita_data.get('service_price', None)
        open_days = cita_data.get('get_open_days', {})
        print(f"Días libres para store={store}, service={service_id}: {open_days}")
        # Mostrar claves y valores de open_days
        if isinstance(open_days, dict):
            for k, v in open_days.items():
                print(f"open_days dict: clave={k}, valor={v}")
        elif isinstance(open_days, list):
            for v in open_days:
                print(f"open_days list: valor={v}")
        # El instanceCode dinámico suele estar en la respuesta de serviceMonthData
        instance_code_dynamic = cita_data.get('instanceCode', instance_code_actual)
        dias_iter = []
        # Solo agregar días que sean fechas reales (no claves tipo 'n0', 'n1')
        if isinstance(open_days, dict):
            dias_iter = [v for v in open_days.values() if isinstance(v, str) and not v.startswith('n')]
        elif isinstance(open_days, list):
            dias_iter = [v for v in open_days if isinstance(v, str) and not v.startswith('n')]
        for dia in dias_iter:
            print(f"Procesando dia: {dia}")
            horas_data = get_service_day_data(store, service_id, instance_code_dynamic, dia)
            print(f"Respuesta completa serviceDayData para store={store}, service={service_id}, dia={dia}: {horas_data}")
            day_slots = horas_data.get('get_day_slots', {})
            hour_prices = horas_data.get('get-hour-prices', '{}')
            import json
            try:
                hour_prices = json.loads(hour_prices)
            except Exception:
                hour_prices = {}
            # Mostrar claves y valores de day_slots
            if isinstance(day_slots, dict):
                for k, v in day_slots.items():
                    print(f"day_slots dict: clave={k}, valor={v}")
            elif isinstance(day_slots, list):
                for v in day_slots:
                    print(f"day_slots list: valor={v}")
            horas_libres = []
            if isinstance(day_slots, dict):
                for slot in day_slots.values():
                    for hora in slot:
                        print(f"slot/hora: {hora}")
                        if isinstance(hora, str) and not hora.startswith('n'):
                            horas_libres.append(hora)
            elif isinstance(day_slots, list):
                for hora in day_slots:
                    print(f"slot/hora: {hora}")
                    if isinstance(hora, str) and not hora.startswith('n'):
                        horas_libres.append(hora)
            print(f"Horas libres para {dia}: {horas_libres}")
            for slot_id in horas_libres:
                url_debug = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=set-hour-debug"
                payload_debug = {
                    "selectedTime": slot_id,
                    "realSelectedTime": slot_id,
                    "instanceCode": instance_code_dynamic,
                    "firstCall": "undefined"
                }
                import requests
                try:
                    resp_debug = requests.post(url_debug, data=payload_debug)
                    debug_data = resp_debug.json()
                    print(f"Respuesta set-hour-debug para slot_id={slot_id}: {debug_data}")
                    hora_real = debug_data.get("selectedTime") or debug_data.get("realSelectedTime")
                except Exception:
                    hora_real = None
                if not hora_real or (isinstance(hora_real, str) and hora_real.startswith('n')):
                    print(f"Hora real no válida para slot_id={slot_id}: {hora_real}")
                    continue
                precio = hour_prices.get(slot_id, service_price)
                sessionid = get_session_id(store, service_id, instance_code_dynamic, dia)
                discount_info = set_discount_followup(store, sessionid, service_id, f"{dia} {hora_real}") if sessionid else None
                fechas_horas.append({
                    "fecha": dia,
                    "hora": hora_real,
                    "precio": precio,
                    "sessionid": sessionid,
                    "discount_info": discount_info
                })
                print(f"Cita agregada: fecha={dia}, hora={hora_real}, precio={precio}")
                if len(fechas_horas) >= n:
                    return fechas_horas
    # No usar break fuera de bucle, solo devolver fechas_horas al final
    return fechas_horas
import requests
from bs4 import BeautifulSoup

# Paso 1: Obtener las provincias disponibles


# Obtiene provincias, estaciones y fechas desde el endpoint AJAX
def get_group_startup(instance_code, store_id="1"):
    url = "https://citaitvsitval.com/ajax/ajaxmodules.php?module=groupStartup"
    payload = {
        "store": str(store_id),
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
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception:
        return {}
