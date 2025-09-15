import requests
import json
import re
import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

class SitValScraper:
    # Scraper for the SitVal ITV appointment system
    
    BASE_URL = "https://citaitvsitval.com"
    AJAX_URL = f"{BASE_URL}/ajax/ajaxmodules.php"
    
    # INSTANCE_CODE_TEMPORAL for testing only, remove if not used
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_headers()
        self._cached_instance_code = None
        self._cache_timestamp = 0
        self._cache_ttl = 1800  # 30 minutes cache
        
    def _setup_headers(self) -> None:
        # Configure headers to simulate browser
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
        """Makes AJAX request with error handling and instanceCode extraction"""
        try:
            response = self.session.post(
                f"{self.AJAX_URL}?module={module}", 
                data=payload, 
                timeout=15
            )
            
            print(f"DEBUG: Respuesta de {module} - Status: {response.status_code}")
            
            # Search for instanceCode in response headers
            for header_name, header_value in response.headers.items():
                if 'instance' in header_name.lower() and len(str(header_value)) >= 25:
                    print(f"InstanceCode encontrado en header {header_name}: {header_value}")
            
            # Save response for debugging
            with open(f"debug_{module}_response.bin", "wb") as f:
                f.write(response.content)
            
            # Handle Brotli compression (optional)
            response_text = response.text
            if response.headers.get('Content-Encoding') == 'br':
                try:
                    import brotli # type: ignore
                    decompressed = brotli.decompress(response.content)
                    response_text = decompressed.decode("utf-8", errors="replace")
                    with open(f"debug_{module}_response.txt", "w", encoding="utf-8") as f:
                        f.write(response_text)
                except ImportError:
                    print("Brotli not available - using response.text directly")
                    response_text = response.text
                    with open(f"debug_{module}_response_fallback.txt", "w", encoding="utf-8") as f:
                        f.write(response_text)
                except Exception as e:
                    print(f"Error descomprimiendo Brotli: {e} - using response.text directly")
                    response_text = response.text
                    with open(f"debug_{module}_response_fallback.txt", "w", encoding="utf-8") as f:
                        f.write(response_text)
            
            # Search for instanceCode in response text before parsing JSON
            instance_patterns = [
                r'"instanceCode"\s*:\s*"([a-zA-Z0-9]{25,})"',
                r"'instanceCode'\s*:\s*'([a-zA-Z0-9]{25,})'",
                r'instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{25,})["\']'
            ]
            
            for pattern in instance_patterns:
                matches = re.findall(pattern, response_text)
                if matches:
                    print(f"InstanceCode encontrado en respuesta de {module}: {matches[0]}")
            
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                # If not valid JSON, try to extract useful data from text
                print(f"Respuesta de {module} no es JSON válido, analizando texto...")
                return {"raw_response": response_text}
                
        except requests.RequestException as e:
            print(f"Error en petición {module}: {e}")
            return {}
        except Exception as e:
            print(f"Error procesando respuesta de {module}: {e}")
            try:
                print(f"Respuesta recibida: {response.text[:500]}...")
            except:
                print("No se pudo obtener el texto de la respuesta.")
            return {}
    def login_by_cookie(self, store_id: str) -> Dict[str, Any]:
        """Performs login-by-cookie request to initialize session for specific station"""
        print(f"DEBUG: login-by-cookie with store={store_id}, session=''")
        
        # First visit main page to establish initial cookies
        try:
            main_response = self.session.get(self.BASE_URL, timeout=10)
            print(f"Main page loaded - Status: {main_response.status_code}")
        except Exception as e:
            print(f"Error loading main page: {e}")
        
        return self._make_request('login-by-cookie', {
            "store": str(store_id),
            "session": ""
        })
    
    def _extract_instance_from_network_flow(self) -> Optional[str]:
        """Simulates complete browser flow to extract instanceCode"""
        try:
            print("Simulando flujo completo del navegador...")
            
            # 1. Load main page
            main_response = self.session.get(self.BASE_URL, timeout=15)
            
            # 2. Search for instanceCode in initial response
            instance_code = self._extract_instance_from_response(main_response.text)
            if instance_code:
                return instance_code
            
            # 3. Simulate loading JavaScript/CSS resources that might contain the code
            soup = BeautifulSoup(main_response.text, 'html.parser')
            
            # Search for external scripts
            for script in soup.find_all('script', src=True):
                try:
                    script_url = script['src']
                    if script_url.startswith('/'):
                        script_url = self.BASE_URL + script_url
                    elif not script_url.startswith('http'):
                        script_url = f"{self.BASE_URL}/{script_url}"
                    
                    script_response = self.session.get(script_url, timeout=10)
                    instance_code = self._extract_instance_from_response(script_response.text)
                    if instance_code:
                        print(f"InstanceCode encontrado en script: {script_url}")
                        return instance_code
                except Exception:
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error en flujo de red: {e}")
            return None
    
    def _extract_instance_from_response(self, text: str) -> Optional[str]:
        """Extrae instanceCode de cualquier texto de respuesta"""
        patterns = [
            r'instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{25,})["\']',
            r'instance_code["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{25,})["\']',
            r'"instanceCode"\s*:\s*"([a-zA-Z0-9]{25,})"',
            r"'instanceCode'\s*:\s*'([a-zA-Z0-9]{25,})'",
            r'var\s+\w*[Ii]nstance\w*\s*=\s*["\']([a-zA-Z0-9]{25,})["\']',
            r'const\s+\w*[Ii]nstance\w*\s*=\s*["\']([a-zA-Z0-9]{25,})["\']',
            r'let\s+\w*[Ii]nstance\w*\s*=\s*["\']([a-zA-Z0-9]{25,})["\']',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match) >= 25 and re.match(r'^[a-zA-Z0-9]+$', match):
                    return match
        
        return None
    
    def get_instance_code_robust(self, store_id: str, force_refresh: bool = False) -> str:
        """Obtiene instanceCode dinámico con cache y múltiples estrategias"""
        
        # Verificar cache si no se fuerza refresh
        if not force_refresh and self._is_cache_valid():
            print(f"✓ Usando instanceCode desde cache: {self._cached_instance_code}")
            return self._cached_instance_code
        
        print("=== Extrayendo instanceCode dinámico ===")

        # Estrategia 1: Análisis completo del flujo de red
        instance_code = self._extract_instance_from_network_flow()
        if instance_code:
            print(f"✓ InstanceCode obtenido del flujo de red: {instance_code}")
            self._cache_instance_code(instance_code)
            return instance_code

        # Estrategia 2: Obtener desde la página principal
        instance_code = self._get_instance_from_main_page()
        if instance_code:
            print(f"✓ InstanceCode obtenido de página principal: {instance_code}")
            self._cache_instance_code(instance_code)
            return instance_code

        # Estrategia 3: Flujo completo con login-by-cookie
        try:
            # Paso 1: login-by-cookie with specific store
            login_response = self.login_by_cookie(store_id)
            
            # Buscar instanceCode en la respuesta del login
            instance_code = self._find_instance_code_recursive(login_response)
            if instance_code:
                print(f"✓ InstanceCode obtenido de login-by-cookie: {instance_code}")
                self._cache_instance_code(instance_code)
                return instance_code

            # Paso 2: startUp con el store especificado
            startup_data = self._make_request('startUp', {
                'store': store_id,
                'itineraryPlace': '0',
                'instanceCode': ''
            })

            instance_code = self._find_instance_code_recursive(startup_data)
            if instance_code:
                print(f"✓ InstanceCode obtenido de startUp: {instance_code}")
                self._cache_instance_code(instance_code)
                return instance_code

            # Paso 3: groupStartup
            group_data = self._make_request('groupStartup', {
                'store': store_id,
                'owner': '1',
                'instanceCode': '',
                'group': '4'
            })

            instance_code = self._find_instance_code_recursive(group_data)
            if instance_code:
                print(f"✓ InstanceCode obtenido de groupStartup: {instance_code}")
                self._cache_instance_code(instance_code)
                return instance_code

        except Exception as e:
            print(f"Error en flujo de login: {e}")

        # Estrategia 4: Buscar en cookies de la sesión
        print("Analizando cookies de la sesión:")
        for cookie in self.session.cookies:
            print(f"  Cookie: {cookie.name} = {cookie.value} (longitud: {len(cookie.value)})")
            if len(cookie.value) >= 25 and re.match(r'^[a-zA-Z0-9]+$', cookie.value):
                print(f"✓ InstanceCode obtenido de cookie {cookie.name}: {cookie.value}")
                self._cache_instance_code(cookie.value)
                return cookie.value

        # Estrategia 5: Fallback con scraping HTML básico
        instance_code = self._get_instance_from_html()
        if instance_code:
            print(f"✓ InstanceCode obtenido por HTML: {instance_code}")
            self._cache_instance_code(instance_code)
            return instance_code

        print("⚠ No se encontró instanceCode específico, usando string vacío")
        print("✓ El sistema funciona correctamente sin instanceCode específico")
        
        # El sistema funciona perfectamente con instanceCode vacío
        return ""
    
    def _is_cache_valid(self) -> bool:
        """Verifica si el cache del instanceCode es válido"""
        if not self._cached_instance_code:
            return False
        
        import time
        return (time.time() - self._cache_timestamp) < self._cache_ttl
    
    def _cache_instance_code(self, instance_code: str) -> None:
        """Guarda el instanceCode en cache"""
        import time
        self._cached_instance_code = instance_code
        self._cache_timestamp = time.time()
        print(f"InstanceCode guardado en cache por {self._cache_ttl} segundos")
    
    def _get_instance_from_main_page(self) -> Optional[str]:
        """Obtiene instanceCode directamente de la página principal con análisis exhaustivo"""
        try:
            print("Intentando obtener instanceCode de la página principal...")
            response = self.session.get(self.BASE_URL, timeout=15)
            response.raise_for_status()
            
            # Guardar HTML para análisis manual si es necesario
            with open("debug_main_page.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            
            html_content = response.text
            print(f"HTML descargado, tamaño: {len(html_content)} caracteres")
            
            # Patrones mejorados y más específicos
            patterns = [
                # Patrones básicos
                r'instanceCode["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{25,})["\']',
                r'instance_code["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{25,})["\']',
                
                # Variables JavaScript
                r'var\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{25,})["\']',
                r'const\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{25,})["\']',
                r'let\s+instanceCode\s*=\s*["\']([a-zA-Z0-9]{25,})["\']',
                
                # JSON objects
                r'"instanceCode"\s*:\s*"([a-zA-Z0-9]{25,})"',
                r"'instanceCode'\s*:\s*'([a-zA-Z0-9]{25,})'",
                
                # Configuraciones comunes
                r'config\s*=\s*{[^}]*instanceCode["\']?\s*:\s*["\']([a-zA-Z0-9]{25,})["\']',
                r'window\.[a-zA-Z_]*[Ii]nstance[a-zA-Z_]*\s*=\s*["\']([a-zA-Z0-9]{25,})["\']',
                
                # Patrones más generales para códigos largos
                r'["\']([a-zA-Z0-9]{32})["\']',  # Códigos de 32 caracteres
                r'["\']([a-z0-9]{30,})["\']',    # Códigos largos en minúsculas
                
                # Patrones en formularios o AJAX
                r'data\s*:\s*{[^}]*["\']([a-zA-Z0-9]{25,})["\']',
                r'instanceCode["\']?\s*:\s*["\']([a-zA-Z0-9]{25,})["\']',
            ]
            
            found_codes = []
            for i, pattern in enumerate(patterns):
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if len(match) >= 25 and re.match(r'^[a-zA-Z0-9]+$', match):
                        print(f"Código encontrado con patrón {i+1}: {match}")
                        found_codes.append(match)
            
            # Si encontramos códigos, devolver el más largo (probablemente más específico)
            if found_codes:
                longest_code = max(found_codes, key=len)
                print(f"Seleccionando código más largo: {longest_code}")
                return longest_code
            
            # Análisis con BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Buscar en todos los scripts
            print("Analizando scripts JavaScript...")
            for i, script in enumerate(soup.find_all('script')):
                if script.string:
                    script_content = script.string
                    # Buscar cualquier string largo que parezca un código
                    long_strings = re.findall(r'["\']([a-zA-Z0-9]{25,})["\']', script_content)
                    for string in long_strings:
                        if len(string) >= 25:
                            print(f"Posible código en script {i}: {string}")
                            found_codes.append(string)
            
            # Buscar en inputs hidden
            hidden_inputs = soup.find_all('input', {'type': 'hidden'})
            for input_elem in hidden_inputs:
                name = input_elem.get('name', '').lower()
                value = input_elem.get('value', '')
                print(f"Input hidden: {name} = {value}")
                if len(value) >= 25 and re.match(r'^[a-zA-Z0-9]+$', value):
                    found_codes.append(value)
            
            # Buscar en atributos data-*
            for element in soup.find_all():
                for attr_name, attr_value in element.attrs.items():
                    if isinstance(attr_value, str) and len(attr_value) >= 25:
                        if re.match(r'^[a-zA-Z0-9]+$', attr_value):
                            print(f"Posible código en atributo {attr_name}: {attr_value}")
                            found_codes.append(attr_value)
            
            # Devolver el código más prometedor
            if found_codes:
                # Filtrar códigos únicos y ordenar por longitud
                unique_codes = list(set(found_codes))
                unique_codes.sort(key=len, reverse=True)
                print(f"Códigos únicos encontrados: {unique_codes}")
                return unique_codes[0]
                        
        except Exception as e:
            print(f"Error obteniendo instanceCode de página principal: {e}")
        
        return None

    def _get_instance_from_html(self) -> Optional[str]:
        """Método de fallback para obtener instanceCode del HTML"""
        try:
            response = self.session.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Patrones de búsqueda básicos
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
    
    def _get_instance_from_session(self, store_id: str = "0") -> Optional[str]:
        """Gets instanceCode from cookies or startup response for specific store"""
        try:
            # Realizar petición inicial
            self.session.get(self.BASE_URL, timeout=10)
            
            # Probar startup with specific store
            startup_data = self._make_request('startUp', {
                'store': str(store_id), 
                'itineraryPlace': '0', 
                'instanceCode': ''
            })
            
            # Probar groupStartup with specific store
            group_data = self._make_request('groupStartup', {
                'store': str(store_id), 
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
        """Busca recursivamente instanceCode en estructura JSON"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Buscar claves que contengan 'instance' o 'code'
                key_lower = key.lower()
                if ('instance' in key_lower or key_lower == 'code') and value:
                    str_value = str(value)
                    if len(str_value) >= 25 and re.match(r'^[a-zA-Z0-9]+$', str_value):
                        return str_value
                
                # Recursión en valores anidados
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
    
    def get_group_startup(self, instance_code: str, store_id: str = None) -> Dict[str, Any]:
        """Gets information about provinces and stations"""
        # If no store_id provided, use "0" for general query
        if store_id is None:
            store_id = "0"
            
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
        
        # Si no tenemos instanceCode, intentar obtener uno específico para esta estación
        if not instance_code:
            instance_code = self.get_instance_code_robust(store)
            
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
        
        # Si no tenemos instanceCode, intentar obtener uno específico para esta estación
        if not instance_code:
            instance_code = self.get_instance_code_robust(store)
            
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
        """Gets next available appointments for specific station and service"""
        print(f"Searching appointments for store={store}, service={service}")
        
        # Create fresh session for this specific station to avoid cross-contamination
        original_session = self.session
        self.session = requests.Session()
        self._setup_headers()
        
        try:
            # FIRST: Check if this station actually has availability according to groupStartup
            print(f"🔍 Checking real availability for store {store}...")
            group_data = self.get_group_startup("", "1")  # Get all stations info
            stations = self.extract_stations(group_data)
            
            # Find this specific station
            target_station = None
            for station in stations:
                if station['store_id'] == store:
                    target_station = station
                    break
            
            if target_station:
                first_availability = target_station.get('primer_dia')
                print(f"   Station {store} ({target_station['nombre']}) first_availability: {first_availability}")
                
                # If no first_availability, the station has no real appointments
                if not first_availability or first_availability == []:
                    print(f"   ❌ Station {store} has no real availability according to groupStartup")
                    return []  # Return empty list - no appointments available
                else:
                    print(f"   ✅ Station {store} has availability starting: {first_availability}")
            else:
                print(f"   ⚠️  Station {store} not found in groupStartup data")
                return []  # Return empty if station not found
            
            # Get instanceCode specific for this station
            if not instance_code or instance_code == "0":
                instance_code = self.get_instance_code_robust(store)
                
            # If still no instanceCode, try with empty string
            if not instance_code or instance_code == "0":
                print("Trying with empty instanceCode...")
                instance_code = ""
            
            slots = []
            today = datetime.date.today()
            
            # Calcular el rango: desde hoy hasta final del mes siguiente
            current_month_start = today.replace(day=1)
            next_month_start = (current_month_start + datetime.timedelta(days=32)).replace(day=1)
            # Final del mes siguiente
            end_of_next_month = (next_month_start + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
            
            print(f"🔍 Buscando citas desde {today} hasta {end_of_next_month}")
            print(f"   Estación: {store}, Servicio: {service}")
            
            # Buscar mes por mes desde el actual hasta el siguiente
            search_months = [
                current_month_start,  # Mes actual
                next_month_start      # Mes siguiente
            ]
            
            for month_start in search_months:
                if len(slots) >= max_slots:
                    break
                
                month_name = month_start.strftime('%B %Y')
                print(f"📅 Consultando {month_name}...")
                    
                # Obtener días disponibles del mes
                month_data = self.get_service_month_data(
                    store, service, instance_code, month_start.strftime('%Y-%m-%d')
                )
                
                open_days = month_data.get('get_open_days', {})
                service_price = month_data.get('service_price')
                
                # Filtrar días válidos en el rango correcto
                valid_days = self._filter_valid_days(open_days)
                
                # Solo tomar fechas desde hoy hasta final del mes siguiente
                filtered_days = []
                for dia in valid_days:
                    try:
                        dia_date = datetime.datetime.strptime(dia, '%Y-%m-%d').date()
                        # Debe estar entre hoy y final del mes siguiente
                        if today <= dia_date <= end_of_next_month:
                            filtered_days.append(dia)
                    except:
                        continue
                
                # Ordenar fechas cronológicamente
                filtered_days.sort()
                
                print(f"   📋 Días disponibles en {month_name}: {len(filtered_days)}")
                
                for dia in filtered_days:
                    if len(slots) >= max_slots:
                        break
                        
                    # Obtener horarios del día
                    day_data = self.get_service_day_data(store, service, instance_code, dia)
                    day_slots = day_data.get('get_day_slots', {})
                    
                    # Extraer horarios válidos
                    valid_hours = self._extract_valid_hours(day_slots)
                    
                    if valid_hours:
                        print(f"   ✅ {dia}: {len(valid_hours)} horarios disponibles")
                        
                        # Solo añadir si realmente hay horarios válidos
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
                    else:
                        print(f"   ❌ {dia}: Sin horarios disponibles - SALTANDO")
            
            return slots
        
        finally:
            # Restore original session
            self.session = original_session
    
    def _filter_valid_days(self, open_days: Any) -> List[str]:
        # Filtra días válidos de la respuesta de disponibilidad
        valid_days = []
        if isinstance(open_days, dict):
            # El sistema devuelve fechas como valores, no como indicadores
            # Formato: {'n0': '2025-09-15', 'n1': '2025-09-16', ...}
            for key, value in open_days.items():
                if isinstance(value, str) and len(value) == 10 and '-' in value:
                    # Validar que sea una fecha válida (YYYY-MM-DD)
                    try:
                        year, month, day = value.split('-')
                        if len(year) == 4 and len(month) == 2 and len(day) == 2:
                            valid_days.append(value)
                    except:
                        continue
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
            for slot_group in day_slots.values():
                if isinstance(slot_group, dict):
                    # Estructura anidada: {"n0": {"n0": "2025-09-15 08:10:00", "n1": "..."}, ...}
                    for hora_str in slot_group.values():
                        h = extract_hour(hora_str)
                        if h:
                            valid_hours.append(h)
                elif isinstance(slot_group, list):
                    # Lista de horarios
                    for hora in slot_group:
                        h = extract_hour(hora)
                        if h:
                            valid_hours.append(h)
                elif isinstance(slot_group, str):
                    # Horario directo
                    h = extract_hour(slot_group)
                    if h:
                        valid_hours.append(h)
        elif isinstance(day_slots, list):
            for hora in day_slots:
                h = extract_hour(hora)
                if h:
                    valid_hours.append(h)
        
        # Eliminar duplicados y ordenar
        return sorted(list(set(valid_hours)))


