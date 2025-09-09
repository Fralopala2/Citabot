import requests
import json
import re
import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

class SitValScraper:
    # Scraper para el sistema de citas ITV SitVal
    
    BASE_URL = "https://citaitvsitval.com"
    AJAX_URL = f"{BASE_URL}/ajax/ajaxmodules.php"
    
    # INSTANCE_CODE_TEMPORAL solo para pruebas, eliminar si no se usa
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_headers()
        
    def _setup_headers(self) -> None:
    # Configura headers para simular navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Origin': self.BASE_URL,
            'Referer': f'{self.BASE_URL}/',
            'Connection': 'keep-alive'
        })
    
    def _make_request(self, module: str, payload: Dict) -> Dict[str, Any]:
    # Realiza petición AJAX con manejo de errores
        try:
            response = self.session.post(
                f"{self.AJAX_URL}?module={module}", 
                data=payload, 
                timeout=10
            )
            print(f"DEBUG: Respuesta cruda de {module}: {response.text}")
            print(f"DEBUG: Status code: {response.status_code}")
            print(f"DEBUG: Headers: {response.headers}")
            # Guardar respuesta cruda en archivo para inspección manual
            with open(f"debug_{module}_response.bin", "wb") as f:
                f.write(response.content)
            # Si la respuesta está comprimida con Brotli, intentar descomprimir
            if response.headers.get('Content-Encoding') == 'br':
                try:
                    import brotli
                    decompressed = brotli.decompress(response.content)
                    with open(f"debug_{module}_response.txt", "w", encoding="utf-8") as f:
                        f.write(decompressed.decode("utf-8", errors="replace"))
                    print(f"DEBUG: Respuesta Brotli descomprimida guardada en debug_{module}_response.txt")
                except Exception as e:
                    print(f"Error descomprimiendo Brotli: {e}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error en petición {module}: {e}")
            return {}
        except Exception as e:
            print("DEBUG: Entrando en except de _make_request")
            print(f"Error decodificando JSON en {module}: {e}")
            try:
                print(f"Respuesta recibida (raw): {response.text}")
            except Exception:
                print("No se pudo obtener el texto de la respuesta.")
            return {}
    def login_by_cookie(self) -> Dict[str, Any]:
    # Realiza la petición login-by-cookie para inicializar la sesión
        print(f"DEBUG: Realizando login-by-cookie con store=1, session=''")
        return self._make_request('login-by-cookie', {
            "store": "1",
            "session": ""
        })
    
    def get_instance_code_robust(self, store_id: str = "23") -> str:
    # Obtiene instanceCode dinámico siguiendo el flujo real de la web
        print("=== Extrayendo instanceCode dinámico ===")

        # Paso 1: login-by-cookie (siempre store=1, session='')
        self.login_by_cookie()

        # Paso 2: startUp y groupStartup con el store real
        startup_data = self._make_request('startUp', {
            'store': store_id,
            'itineraryPlace': '0',
            'instanceCode': ''
        })

        group_data = self._make_request('groupStartup', {
            'store': store_id,
            'owner': '1',
            'instanceCode': '',
            'group': '4'
        })

        # Buscar en cookies
        for cookie in self.session.cookies:
            if len(cookie.value) >= 25 and re.match(r'^[a-zA-Z0-9]+$', cookie.value):
                print(f"✓ InstanceCode obtenido de cookie: {cookie.value}")
                return cookie.value

        # Buscar en respuesta JSON
        instance_code = self._find_instance_code_recursive(startup_data)
        if not instance_code:
            instance_code = self._find_instance_code_recursive(group_data)
        if instance_code:
            print(f"✓ InstanceCode obtenido de respuesta JSON: {instance_code}")
            return instance_code

        # Fallback: Scraping HTML
        instance_code = self._get_instance_from_html()
        if instance_code:
            print(f"✓ InstanceCode obtenido por HTML: {instance_code}")
            return instance_code

        print("⚠ No se pudo obtener instanceCode válido")
        return ""
    
    def _get_instance_from_html(self) -> Optional[str]:
    # Extrae instanceCode del HTML de la página principal
        try:
            response = self.session.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Patrones de búsqueda
            patterns = [
                r'instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
                r'instance_code["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{20,})["\']',
                r'var\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']',
                r'const\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{20,})["\']'
            ]
            
            # Buscar en scripts
            for script in soup.find_all('script'):
                if script.string:
                    for pattern in patterns:
                        match = re.search(pattern, script.string, re.IGNORECASE)
                        if match and len(match.group(1)) >= 20:
                            return match.group(1)
            
            # Buscar en atributos DOM
            for attr in ['data-instance-code', 'data-instancecode', 'instancecode']:
                elements = soup.find_all(attrs={attr: True})
                for element in elements:
                    value = element.get(attr)
                    if value and len(value) >= 20:
                        return value
                        
        except Exception as e:
            print(f"Error en scraping HTML: {e}")
        
        return None
    
    def _get_instance_from_session(self) -> Optional[str]:
    # Obtiene instanceCode desde cookies o respuesta de startup
        try:
            # Realizar petición inicial
            self.session.get(self.BASE_URL, timeout=10)
            
            # Probar startup
            startup_data = self._make_request('startUp', {
                'store': '1', 
                'itineraryPlace': '0', 
                'instanceCode': ''
            })
            
            # Probar groupStartup
            group_data = self._make_request('groupStartup', {
                'store': '1', 
                'owner': '1', 
                'instanceCode': '', 
                'group': '4'
            })
            
            # Buscar en cookies
            for cookie in self.session.cookies:
                if len(cookie.value) >= 25 and re.match(r'^[a-z0-9]+$', cookie.value):
                    return cookie.value
            
            # Buscar en respuesta JSON
            instance_code = self._find_instance_code_recursive(group_data)
            if instance_code:
                return instance_code
                
        except Exception as e:
            print(f"Error obteniendo instanceCode de sesión: {e}")
        
        return None
    
    def _find_instance_code_recursive(self, obj: Any) -> Optional[str]:
    # Busca recursivamente instanceCode en estructura JSON
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == 'instanceCode' and value and len(str(value)) >= 25:
                    return str(value)
                if isinstance(value, (dict, list)):
                    result = self._find_instance_code_recursive(value)
                    if result:
                        return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_instance_code_recursive(item)
                if result:
                    return result
        return None
    
    def get_group_startup(self, instance_code: str, store_id: str = "1") -> Dict[str, Any]:
    # Obtiene información de provincias y estaciones
        return self._make_request('groupStartup', {
            "store": str(store_id),
            "owner": "1",
            "instanceCode": instance_code,
            "group": "4"
        })
    
    def get_service_month_data(self, store: str, service: str, instance_code: str, 
                              date: str = None) -> Dict[str, Any]:
    # Obtiene disponibilidad mensual para una estación y servicio
        if date is None:
            date = datetime.date.today().strftime('%Y-%m-%d')
            
        return self._make_request('serviceMonthData', {
            "store": str(store),
            "itineraryPlace": "0",
            "instanceCode": instance_code,
            "firstCall": "true",
            "date": date,
            "service": str(service)
        })
    
    def get_service_day_data(self, store: str, service: str, instance_code: str, 
                            dia: str) -> Dict[str, Any]:
    # Obtiene horarios disponibles para un día específico
        return self._make_request('serviceDayData', {
            "store": str(store),
            "service": str(service),
            "instanceCode": instance_code,
            "date": dia,
            "itineraryPlace": "0",
            "dateHour": dia
        })
    
    def extract_stations(self, group_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Extrae información de estaciones del response de groupStartup
        print(f"DEBUG: INICIO extract_stations con group_data: {group_data}")
        estaciones = []
        if not group_data or 'groups' not in group_data:
            print("DEBUG: group_data vacío o sin 'groups'")
            return estaciones
        for prov_data in group_data['groups'].values():
            provincia = prov_data.get('name', '')
            for level2_data in prov_data.get('level2', {}).values():
                tipo = level2_data.get('name', '')
                for store_data in level2_data.get('stores', {}).values():
                    estacion = {
                        'provincia': provincia,
                        'tipo': tipo,
                        'nombre': store_data.get('name', ''),
                        'store_id': store_data.get('store', ''),
                        'direccion': store_data.get('short_description', ''),
                        'primer_dia': store_data.get('first_availability'),
                        'instanceCode': store_data.get('instanceCode', '')
                    }
                    estaciones.append(estacion)
        print(f"DEBUG: estaciones encontradas: {estaciones}")
        return estaciones
    
    def get_next_available_slots(self, store: str, service: str, instance_code: str, 
                               max_slots: int = 10) -> List[Dict[str, Any]]:
    # Obtiene las próximas citas disponibles
        print(f"Buscando citas para store={store}, service={service}")
        
        # Usar instanceCode robusto si no se proporciona uno válido
        if not instance_code or instance_code == "0":
            instance_code = self.get_instance_code_robust()
            
        if not instance_code:
            print("No se pudo obtener instanceCode válido")
            return []
        
        slots = []
        today = datetime.date.today()
        
        # Buscar en los próximos 2 meses
        for month_offset in range(2):
            if len(slots) >= max_slots:
                break
                
            search_date = (today.replace(day=1) + 
                          datetime.timedelta(days=32 * month_offset)).replace(day=1)
            
            # Obtener días disponibles del mes
            month_data = self.get_service_month_data(
                store, service, instance_code, search_date.strftime('%Y-%m-%d')
            )
            
            open_days = month_data.get('get_open_days', {})
            service_price = month_data.get('service_price')
            
            # Filtrar días válidos
            valid_days = self._filter_valid_days(open_days)
            
            for dia in valid_days:
                if len(slots) >= max_slots:
                    break
                    
                # Obtener horarios del día
                day_data = self.get_service_day_data(store, service, instance_code, dia)
                day_slots = day_data.get('get_day_slots', {})
                
                # Extraer horarios válidos
                valid_hours = self._extract_valid_hours(day_slots)
                
                for hora in valid_hours:
                    slots.append({
                        'fecha': dia,
                        'hora': hora,
                        'precio': service_price,
                        'store': store,
                        'service': service
                    })
                    if len(slots) >= max_slots:
                        break
        
        return slots
    
    def _filter_valid_days(self, open_days: Any) -> List[str]:
    # Filtra días válidos de la respuesta de disponibilidad
        valid_days = []
        if isinstance(open_days, dict):
            # Claves donde el valor es "1" (disponible)
            valid_days = [k for k, v in open_days.items() if v == "1"]
        elif isinstance(open_days, list):
            valid_days = [v for v in open_days if isinstance(v, str) and not v.startswith('n')]
        return valid_days
    
    def _extract_valid_hours(self, day_slots: Any) -> List[str]:
    # Extrae horarios válidos en formato HH:MM de los slots del día
        valid_hours = []
        def extract_hour(hora_str):
            # Extrae HH:MM de 'YYYY-MM-DD HH:MM:SS'
            if isinstance(hora_str, str) and len(hora_str) >= 16:
                return hora_str[11:16]
            return None
        if isinstance(day_slots, dict):
            for slot in day_slots.values():
                if isinstance(slot, list):
                    for hora in slot:
                        h = extract_hour(hora)
                        if h:
                            valid_hours.append(h)
                elif isinstance(slot, str):
                    h = extract_hour(slot)
                    if h:
                        valid_hours.append(h)
        elif isinstance(day_slots, list):
            for hora in day_slots:
                h = extract_hour(hora)
                if h:
                    valid_hours.append(h)
        return valid_hours


