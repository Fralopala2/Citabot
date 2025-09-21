import requests
import json
import re
import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

class SitValScraper:
    """Scraper for the SitVal ITV appointment system with minimal logging"""
    
    BASE_URL = "https://citaitvsitval.com"
    AJAX_URL = f"{BASE_URL}/ajax/ajaxmodules.php"
    
    def __init__(self):
        self.session = requests.Session()
        self._setup_headers()
    
    def _setup_headers(self):
        """Set up common headers for requests"""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none"
        })

    def _make_request(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """Make a request with error handling and minimal logging"""
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Only log errors, not success
            if response.status_code != 200:
                print(f"⚠️ HTTP {response.status_code} for {url}")
            
            # Check if content is actually compressed
            content_encoding = response.headers.get('Content-Encoding', '').lower()
            
            if content_encoding == 'br':
                # Check if content is already text (requests auto-decompressed)
                try:
                    # Try to decode as text first - if it works, it's already decompressed
                    test_text = response.content.decode('utf-8', errors='replace')
                    if test_text.strip().startswith(('<!DOCTYPE', '<html', '{')):
                        # Content is already readable, just remove the misleading header
                        response.headers.pop('Content-Encoding', None)
                        print(f"✅ Content already decompressed by requests for {url}")
                    else:
                        # Try manual Brotli decompression
                        import brotli
                        decompressed = brotli.decompress(response.content)
                        response._content = decompressed
                        response.headers.pop('Content-Encoding', None)
                        print(f"✅ Manual Brotli decompression: {len(decompressed)} bytes for {url}")
                except ImportError:
                    print("⚠️ Brotli library not available - using content as-is")
                except Exception as e:
                    # If Brotli fails, assume content is already good
                    response.headers.pop('Content-Encoding', None)
                    print(f"ℹ️ Using content as-is for {url} (Brotli header may be incorrect)")
            
            return response
            
        except requests.RequestException as e:
            print(f"❌ Request failed for {url}: {e}")
            raise

    def _make_ajax_request(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make AJAX request and return JSON response"""
        try:
            response = self._make_request(
                url,
                method="POST", 
                data=data,
                headers={"X-Requested-With": "XMLHttpRequest"}
            )
            
            # Try to parse as JSON
            try:
                return response.json()
            except json.JSONDecodeError:
                print(f"⚠️ Response is not valid JSON, returning raw text")
                return {"raw_response": response.text}
                
        except Exception as e:
            print(f"❌ AJAX request failed: {e}")
            return {}

    def search_appointments(self, province_id: str = "2", service_id: str = "1", 
                          office_id: str = "1", year: str = None, month: str = None) -> Dict[str, Any]:
        """Search for available ITV appointments"""
        
        # Use current date if not specified
        if year is None:
            current_date = datetime.datetime.now()
            year = str(current_date.year)
            month = str(current_date.month)
        
        # Step 1: Get main page and extract instance code
        main_response = self._make_request(self.BASE_URL)
        instance_code = self._extract_instance_code(main_response)
        
        if not instance_code:
            print("⚠️ Could not find instance code")
            return {"error": "Instance code not found", "appointments": [], "found_count": 0}
        
        # Step 2: Search for appointments
        search_data = {
            "module": "appointments",
            "province": province_id,
            "service": service_id,
            "office": office_id,
            "year": year,
            "month": month,
            "instanceCode": instance_code
        }
        
        appointments_response = self._make_request(
            self.AJAX_URL,
            method="POST",
            data=search_data,
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        
        # Parse appointments
        appointments = self._parse_appointments(appointments_response.text)
        
        result = {
            "province_id": province_id,
            "service_id": service_id,
            "office_id": office_id,
            "year": year,
            "month": month,
            "instance_code": instance_code,
            "appointments": appointments,
            "found_count": len(appointments),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Only log when appointments are found
        if appointments:
            print(f"✅ Found {len(appointments)} appointments for {year}/{month}")
        
        return result

    def _extract_instance_code(self, response: requests.Response) -> Optional[str]:
        """Extract instance code from response"""
        
        # Try headers first
        for header_name, header_value in response.headers.items():
            if 'instance' in header_name.lower() and len(str(header_value)) >= 25:
                return str(header_value)
        
        # Try HTML content
        content = response.text
        patterns = [
            r'instanceCode["\']?\s*[:=]\s*["\']([^"\']{25,})["\']',
            r'instance["\']?\s*[:=]\s*["\']([^"\']{25,})["\']',
            r'var\s+instanceCode\s*=\s*["\']([^"\']{25,})["\']',
            r'data-instance["\']?\s*=\s*["\']([^"\']{25,})["\']'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None

    def _parse_appointments(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse appointment data from HTML response"""
        
        if not html_content or html_content.strip() == "":
            return []

    def get_group_startup(self, instance_code: str = "", store_id: str = "1") -> Dict[str, Any]:
        """Gets information about provinces and stations via AJAX call"""
        print(f"🌐 Making groupStartup AJAX call...")
        
        # Make AJAX request for groupStartup
        data = {
            "store": str(store_id),
            "owner": "1", 
            "instanceCode": instance_code,
            "group": "4"
        }
        
        try:
            response = self._make_ajax_request(
                self.AJAX_URL + "?module=groupStartup",
                data
            )
            
            print(f"✅ GroupStartup response received")
            return response
            
        except Exception as e:
            print(f"⚠️ Error getting groupStartup data: {e}")
            return {}

    def extract_stations(self, group_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract stations information from groupStartup JSON response"""
        print(f"🏢 Extracting stations from groupStartup data...")
        
        estaciones = []
        
        if not group_data or 'groups' not in group_data:
            print("⚠️ No 'groups' data found in response")
            return estaciones
            
        try:
            groups = group_data['groups']
            print(f"📋 Found {len(groups)} province groups")
            
            for prov_key, prov_data in groups.items():
                provincia = prov_data.get('name', 'Unknown')
                print(f"   📍 Processing province: {provincia}")
                
                level2_data = prov_data.get('level2', {})
                for type_key, type_data in level2_data.items():
                    tipo = type_data.get('name', 'ITV')
                    stores = type_data.get('stores', {})
                    
                    print(f"      🏪 Found {len(stores)} stores for type: {tipo}")
                    
                    for store_key, store_data in stores.items():
                        estacion = {
                            'store_id': store_data.get('store', store_key),
                            'provincia': provincia,
                            'nombre': store_data.get('name', ''),
                            'tipo': tipo,
                            'direccion': store_data.get('short_description', ''),
                            'primer_dia': store_data.get('first_availability'),
                            'instanceCode': store_data.get('instanceCode', '')
                        }
                        
                        estaciones.append(estacion)
                        print(f"         ✅ Added: {estacion['nombre']} (ID: {estacion['store_id']})")
            
            print(f"🎉 Total stations extracted: {len(estaciones)}")
            return estaciones
            
        except Exception as e:
            print(f"⚠️ Error extracting stations: {e}")
            return []

    def _parse_station_info(self, text: str, value: str) -> Optional[Dict[str, Any]]:
        """Parse station information from option text"""
        try:
            # Common patterns for station text
            # Example: "VALENCIA - Valencia Centro (ITV)"
            parts = text.split(' - ')
            
            if len(parts) >= 2:
                provincia = parts[0].strip()
                resto = parts[1].strip()
                
                # Try to separate name and type
                if '(' in resto and ')' in resto:
                    nombre = resto.split('(')[0].strip()
                    tipo = resto.split('(')[1].replace(')', '').strip()
                else:
                    nombre = resto
                    tipo = "ITV"
                
                return {
                    "store_id": value,
                    "provincia": provincia,
                    "nombre": nombre,
                    "tipo": tipo
                }
            else:
                # Simple format
                return {
                    "store_id": value,
                    "provincia": "Unknown",
                    "nombre": text,
                    "tipo": "ITV"
                }
                
        except Exception as e:
            print(f"⚠️ Error parsing station info for '{text}': {e}")
            
        return None

    def _extract_stations_fallback(self, html_content: str) -> List[Dict[str, Any]]:
        """Fallback method to extract stations using regex patterns"""
        stations = []
        
        print("🔍 Using fallback regex patterns to find stations...")
        
        # Pattern 1: ITV station names with common prefixes
        itv_patterns = [
            r'ITV\s+([A-Za-zÀ-ÿ\s\-\.]+)',
            r'ESTACIÓN\s+ITV\s+([A-Za-zÀ-ÿ\s\-\.]+)',
            r'CENTRO\s+ITV\s+([A-Za-zÀ-ÿ\s\-\.]+)',
            r'>([A-Za-zÀ-ÿ\s\-\.]+\s+ITV)<',
            r'"([A-Za-zÀ-ÿ\s\-\.]+\s+ITV)"'
        ]
        
        for i, pattern in enumerate(itv_patterns):
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            print(f"   Pattern {i+1}: Found {len(matches)} matches")
            
            for j, match in enumerate(matches[:10]):  # Limit to first 10 for debugging
                if len(match.strip()) > 3:  # Avoid very short matches
                    station_id = f"fallback_{i}_{j}"
                    stations.append({
                        "store_id": station_id,
                        "provincia": "Regex",
                        "nombre": match.strip(),
                        "tipo": "ITV"
                    })
        
        # Pattern 2: Look for data attributes or JSON-like structures
        data_patterns = [
            r'data-station[^=]*=\s*["\']([^"\']+)["\']',
            r'data-store[^=]*=\s*["\']([^"\']+)["\']',
            r'"station[^"]*"\s*:\s*"([^"]+)"',
            r'"store[^"]*"\s*:\s*"([^"]+)"'
        ]
        
        for i, pattern in enumerate(data_patterns):
            matches = re.findall(pattern, html_content)
            print(f"   Data pattern {i+1}: Found {len(matches)} matches")
            
            for j, match in enumerate(matches[:5]):
                stations.append({
                    "store_id": f"data_{i}_{j}",
                    "provincia": "DataAttr",
                    "nombre": match.strip(),
                    "tipo": "ITV"
                })
        
        # Pattern 3: Look for city/location names that might be ITV stations
        location_patterns = [
            r'value\s*=\s*["\'](\d+)["\'][^>]*>([A-Za-zÀ-ÿ\s\-\.]{5,40})<',
            r'<option[^>]+value\s*=\s*["\']([^"\']+)["\'][^>]*>([^<]{5,40})</option>'
        ]
        
        for i, pattern in enumerate(location_patterns):
            matches = re.findall(pattern, html_content)
            print(f"   Location pattern {i+1}: Found {len(matches)} matches")
            
            for match in matches[:10]:
                if len(match) == 2:
                    value, text = match
                    if value and text.strip() and value not in ['0', '', 'null']:
                        stations.append({
                            "store_id": value,
                            "provincia": "Location",
                            "nombre": text.strip(),
                            "tipo": "ITV"
                        })
        
        print(f"🔄 Fallback extraction found {len(stations)} total matches")
        return stations
        
        appointments = []
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for appointment containers
            appointment_elements = soup.find_all(['div', 'li', 'tr'], 
                                               class_=re.compile(r'appointment|cita|available', re.I))
            
            if not appointment_elements:
                appointment_elements = soup.find_all(['div', 'li', 'tr'], attrs={'data-date': True})
            
            if not appointment_elements:
                appointment_elements = soup.find_all(string=re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'))
                
            for element in appointment_elements:
                appointment = self._extract_appointment_data(element)
                if appointment:
                    appointments.append(appointment)
                    
        except Exception:
            # Fallback: regex search for dates
            date_patterns = [
                r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, html_content)
                for match in matches:
                    try:
                        if len(match) == 3:
                            day, month, year = match
                            if len(year) == 2:
                                year = "20" + year
                            
                            appointments.append({
                                "date": f"{day}/{month}/{year}",
                                "time": "Unknown",
                                "available": True,
                                "location": "Unknown"
                            })
                    except:
                        continue
        
        return appointments

    def _extract_appointment_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract appointment data from HTML element"""
        
        if isinstance(element, str):
            date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', element)
            if date_match:
                day, month, year = date_match.groups()
                if len(year) == 2:
                    year = "20" + year
                return {
                    "date": f"{day}/{month}/{year}",
                    "time": "Unknown",
                    "available": True,
                    "location": "Unknown"
                }
            return None
        
        try:
            text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
            
            date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', text)
            if not date_match:
                return None
            
            day, month, year = date_match.groups()
            if len(year) == 2:
                year = "20" + year
            
            time_match = re.search(r'(\d{1,2}):(\d{2})', text)
            time_str = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else "Unknown"
            
            available = True
            if any(word in text.lower() for word in ['ocupado', 'no disponible', 'lleno', 'cerrado']):
                available = False
            
            location = "Unknown"
            if hasattr(element, 'get') and element.get('data-location'):
                location = element.get('data-location')
            
            return {
                "date": f"{day}/{month}/{year}",
                "time": time_str,
                "available": available,
                "location": location,
                "raw_text": text[:50]  # Reduced from 100 to minimize output
            }
            
        except Exception:
            return None

# Test function (minimal output)
def test_scraper():
    """Test the scraper functionality with minimal output"""
    scraper = SitValScraper()
    
    print("🧪 Testing scraper...")
    result = scraper.search_appointments()
    print(f"📊 Results: {result['found_count']} appointments found")
    
    return result

if __name__ == "__main__":
    test_scraper()
