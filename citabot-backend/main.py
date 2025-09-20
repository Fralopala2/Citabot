import json
import threading
import time
import os
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from notifier import register_device_token, send_new_appointment_notification, get_registered_tokens_count, is_firebase_enabled
from scraper_sitval import SitValScraper



scraper = SitValScraper()
app = FastAPI(
    title="Citabot API",
    description="API para consultar citas ITV en tiempo real",
    version="1.0.0"
)

# Configure CORS for production - restricted to known domains
allowed_origins = [
    "https://citabot.onrender.com",  # Tu dominio de producción
    "http://localhost:3000",         # Desarrollo web local
    "http://127.0.0.1:3000",        # Desarrollo web local alternativo
    # Agregar más dominios según necesites
]

# En desarrollo, permitir localhost
if os.getenv("ENVIRONMENT") == "development":
    allowed_origins.extend([
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://10.0.2.2:8000",  # Android emulator
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Solo métodos necesarios
    allow_headers=["Content-Type", "Authorization"],  # Solo headers necesarios
)

# In-memory cache for available slots
slots_cache = {}
slots_cache_lock = threading.Lock()

# More conservative cache configuration to avoid bans
CACHE_TTL = 1800  # 30 minutes (more conservative)
BACKGROUND_REFRESH_INTERVAL = 900  # 15 minutes between background updates
MAX_CONCURRENT_REQUESTS = 2  # Maximum 2 simultaneous requests to scraper
REQUEST_DELAY = 5  # 5 seconds between requests to be respectful

# Semaphore to limit concurrent requests
scraper_semaphore = threading.Semaphore(MAX_CONCURRENT_REQUESTS)

# Health check endpoint
@app.get("/")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Citabot API",
        "version": "1.0.0",
        "cache_entries": len(slots_cache)
    }

def cache_key(store, service):
    return f"{store}:{service}"

def get_cached_slots(store, service):
    key = cache_key(store, service)
    with slots_cache_lock:
        entry = slots_cache.get(key)
        if entry and (time.time() - entry['timestamp'] < CACHE_TTL):
            return entry['data']
    return None

def detect_new_appointments(old_data, new_data, store, service):
    """Detects new appointments by comparing old and new data"""
    if not old_data or not new_data:
        return []
    
    # Create sets of appointment identifiers for comparison
    old_appointments = set()
    for item in old_data:
        if isinstance(item, dict) and 'fecha' in item and 'hora' in item:
            old_appointments.add(f"{item['fecha']}_{item['hora']}")
    
    new_appointments = []
    for item in new_data:
        if isinstance(item, dict) and 'fecha' in item and 'hora' in item:
            appointment_id = f"{item['fecha']}_{item['hora']}"
            if appointment_id not in old_appointments:
                # This is a new appointment
                new_appointments.append({
                    'estacion': f"Estación {store} - Servicio {service}",
                    'fecha': item['fecha'],
                    'hora': item['hora']
                })
    
    if new_appointments:
        print(f"Detected {len(new_appointments)} new appointments for store {store}, service {service}")
    
    return new_appointments

def set_cached_slots(store, service, data):
    key = cache_key(store, service)
    
    with slots_cache_lock:
        # Check if there are new appointments
        old_data = slots_cache.get(key, {}).get('data', [])
        new_appointments = detect_new_appointments(old_data, data, store, service)
        
        # Update cache
        slots_cache[key] = {'data': data, 'timestamp': time.time()}
        
        # Send notifications for new appointments
        if new_appointments:
            for appointment in new_appointments:
                send_new_appointment_notification(
                    appointment['estacion'],
                    appointment['fecha'], 
                    appointment['hora']
                )

# Background thread to refresh cache periodically
def background_cache_refresher():
    """Updates available appointments cache in background respectfully"""
    while True:
        try:
            # Refresh all keys that are already in cache
            with slots_cache_lock:
                keys = list(slots_cache.keys())
            
            if keys:
                print(f"Refreshing cache for {len(keys)} station-service combinations...")
                
                for i, key in enumerate(keys):
                    try:
                        # Use semaphore to limit concurrent requests
                        with scraper_semaphore:
                            store, service = key.split(":")
                            print(f"   Updating {key} ({i+1}/{len(keys)})")
                            
                            # Use empty instanceCode as it works perfectly
                            data = scraper.get_next_available_slots(store, service, "", 10)
                            set_cached_slots(store, service, data)
                            
                            # Delay between quests s to be respectful
                            if i < len(keys) - 1:  # No delay after the last one
                                time.sleep(REQUEST_DELAY)
                                
                    except Exception as e:
                        print(f"   Error refreshing cache for {key}: {e}")
                
                print("Cache refreshed completely")
            else:
                print("No cache entries to refresh")
                
        except Exception as e:
            print(f"Error in background_cache_refresher: {e}")
        
        # Wait for configured interval before next refresh
        time.sleep(BACKGROUND_REFRESH_INTERVAL)

threading.Thread(target=background_cache_refresher, daemon=True).start()

# Endpoint to get available services by station
@app.get("/itv/servicios")
def get_servicios(store_id: str):
    # Llamar a startUp para obtener los servicios reales de la estación
    startup_data = scraper._make_request('startUp', {'store': store_id})
    categories = startup_data.get('categoriesServices') or {}
    print(f"[DEBUG] categoriesServices extraído de startUp: {json.dumps(categories, ensure_ascii=False)[:2000]}")
    servicios = []
    for cat in categories.values():
        cat_name = cat.get('name')
        services = cat.get('services') or {}
        for serv in services.values():
            service_id = serv.get('id')
            nombre = serv.get('name')
            if nombre and service_id:
                servicios.append({'nombre': nombre, 'service': service_id, 'categoria': cat_name})
    print(f"[DEBUG] servicios extraídos de categoriesServices: {servicios}")
    return {"servicios": servicios}




# Endpoint para registrar el token FCM
@app.post("/register-token")
async def register_token_endpoint(request: Request):
    try:
        data = await request.json()
        token = data.get("token")
        
        if not token:
            return {"error": "Token is required"}, 400
        
        success = register_device_token(token)
        if success:
            return {
                "status": "success", 
                "message": "Token registered successfully",
                "registered_devices": get_registered_tokens_count()
            }
        else:
            return {"error": "Invalid token format"}, 400
            
    except Exception as e:
        print(f"Error registering token: {e}")
        return {"error": "Failed to register token"}, 500


# Endpoint to get all real stations
@app.get("/itv/estaciones")
def get_estaciones():
    """Gets all available ITV stations"""
    print("Getting ITV stations list...")
    
    # Use store_id "1" to get all stations (any valid store_id works)
    instance_code = ""
    group_data = scraper.get_group_startup(instance_code, "1")
    estaciones = scraper.extract_stations(group_data)
    
    print(f"Estaciones obtenidas: {len(estaciones)}")
    return {"estaciones": estaciones}


# Endpoint to get upcoming real appointment dates and times (with cache)
@app.get("/itv/fechas")
def get_fechas(store: str, service: str, n: int = 3):
    """Gets next available appointments for a station and service"""
    print(f"Searching appointments for station {store}, service {service}")
    
    # Try to get from cache first
    cached = get_cached_slots(store, service)
    if cached:
        print(f"Returning {len(cached[:n])} appointments from cache")
        return {"fechas_horas": cached[:n]}
    
    # If not in cache, get with concurrency control
    print(f"No cache, getting fresh data...")
    
    try:
        # Use semaphore to limit concurrent requests
        with scraper_semaphore:
            # Use empty instanceCode as it works perfectly
            fechas_horas = scraper.get_next_available_slots(store, service, "", n)
            set_cached_slots(store, service, fechas_horas)
            
            print(f"Got {len(fechas_horas)} new appointments")
            return {"fechas_horas": fechas_horas}
            
    except Exception as e:
        print(f"Error getting appointments: {e}")
        # Return empty array in case of error
        return {"fechas_horas": []}
# Endpoint para estadísticas de notificaciones
@app.get("/notifications/stats")
def get_notification_stats():
    """Returns notification system statistics"""
    firebase_enabled = is_firebase_enabled()
    return {
        "registered_devices": get_registered_tokens_count(),
        "firebase_enabled": firebase_enabled,
        "status": "active" if firebase_enabled else "disabled"
    }

# Endpoint para probar notificaciones
@app.post("/notifications/test")
async def test_notification(request: Request):
    """Test endpoint to send a notification to a specific token"""
    try:
        data = await request.json()
        token = data.get("token")
        
        if not token:
            return {"error": "Token is required"}, 400
        
        # Send test notification
        success = send_new_appointment_notification(
            "Estación de Prueba",
            "2025-12-25", 
            "10:30",
            specific_token=token
        )
        
        if success:
            return {
                "status": "success", 
                "message": "Test notification sent successfully"
            }
        else:
            return {"error": "Failed to send notification"}, 500
            
    except Exception as e:
        print(f"Error sending test notification: {e}")
        return {"error": "Failed to send test notification"}, 500

# Endpoint to monitor cache status
@app.get("/cache/status")
def get_cache_status():
    """Returns information about cache status"""
    with slots_cache_lock:
        cache_info = []
        current_time = time.time()
        
        for key, entry in slots_cache.items():
            age_seconds = current_time - entry['timestamp']
            age_minutes = age_seconds / 60
            is_expired = age_seconds > CACHE_TTL
            
            cache_info.append({
                'key': key,
                'entries': len(entry['data']),
                'age_minutes': round(age_minutes, 1),
                'is_expired': is_expired,
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry['timestamp']))
            })
    
    return {
        'total_entries': len(slots_cache),
        'cache_ttl_minutes': CACHE_TTL / 60,
        'refresh_interval_minutes': BACKGROUND_REFRESH_INTERVAL / 60,
        'max_concurrent_requests': MAX_CONCURRENT_REQUESTS,
        'request_delay_seconds': REQUEST_DELAY,
        'entries': cache_info
    }

# Endpoint to manually clear cache
@app.post("/cache/clear")
def clear_cache():
    """Clears all cache"""
    with slots_cache_lock:
        cleared_entries = len(slots_cache)
        slots_cache.clear()
    
    return {
        "message": f"Cache cleared. {cleared_entries} entries removed."
    }

# Debug endpoint to see raw scraper data
@app.get("/debug/fechas")
def debug_fechas(store: str, service: str):
    """Debug endpoint to see raw scraper response"""
    try:
        print(f"DEBUG: Getting raw data for store={store}, service={service}")
        
        # Get fresh data without cache
        with scraper_semaphore:
            # Get instanceCode
            instance_code = scraper.get_instance_code_robust(store)
            print(f"DEBUG: instanceCode = {instance_code}")
            
            # Get month data
            import datetime
            today = datetime.date.today()
            month_data = scraper.get_service_month_data(store, service, instance_code, today.strftime('%Y-%m-%d'))
            print(f"DEBUG: month_data keys = {list(month_data.keys())}")
            
            open_days = month_data.get('get_open_days', {})
            print(f"DEBUG: open_days = {open_days}")
            
            # Get first available day
            valid_days = scraper._filter_valid_days(open_days)
            print(f"DEBUG: valid_days = {valid_days}")
            
            if valid_days:
                first_day = valid_days[0]
                print(f"DEBUG: Checking day {first_day}")
                
                # Get day data
                day_data = scraper.get_service_day_data(store, service, instance_code, first_day)
                print(f"DEBUG: day_data keys = {list(day_data.keys())}")
                
                day_slots = day_data.get('get_day_slots', {})
                print(f"DEBUG: day_slots = {day_slots}")
                
                valid_hours = scraper._extract_valid_hours(day_slots)
                print(f"DEBUG: valid_hours = {valid_hours}")
                
                return {
                    "store": store,
                    "service": service,
                    "instance_code": instance_code,
                    "first_day": first_day,
                    "raw_day_slots": day_slots,
                    "extracted_hours": valid_hours,
                    "month_data_keys": list(month_data.keys()),
                    "day_data_keys": list(day_data.keys())
                }
            else:
                return {
                    "store": store,
                    "service": service,
                    "error": "No valid days found",
                    "raw_open_days": open_days
                }
                
    except Exception as e:
        return {
            "error": str(e),
            "store": store,
            "service": service
        }