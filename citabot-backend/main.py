import json
import threading
import time
import os
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from notifier import register_device_token, send_new_appointment_notification, get_registered_tokens_count, is_firebase_enabled, update_user_favorites
from scraper_sitval import SitValScraper

# Server startup time for health checks
startup_time = time.time()


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

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize server"""
    print("🚀 Citabot server started")

# In-memory cache for available slots
slots_cache = {}
slots_cache_lock = threading.Lock()

# More conservative cache configuration to avoid bans
CACHE_TTL = 3600  # 1 hour (more conservative)
BACKGROUND_REFRESH_INTERVAL = 3600  # 1 hour between background updates
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

@app.get("/health")
def detailed_health_check():
    """Detailed health check for server initialization status"""
    # Test if we can actually get stations to determine if server is ready
    server_ready = False
    stations_available = False
    
    try:
        # Try to get stations to verify the scraper actually works
        group_data = scraper.get_group_startup("", "1")
        estaciones = scraper.extract_stations(group_data)
        stations_available = len(estaciones) > 0
        
        # Server is ready if we can get stations OR we have cache entries
        server_ready = stations_available or len(slots_cache) > 0
        
    except Exception as e:
        print(f"⚠️ Health check station test failed: {e}")
        # Fallback: consider ready after 2 minutes if station test fails
        server_ready = time.time() > (startup_time + 120)
    
    details = {
        "status": "ready" if server_ready else "initializing",
        "server_ready": server_ready,
        "stations_available": stations_available,
        "firebase_enabled": is_firebase_enabled(),
        "cache_entries": len(slots_cache),
        "services": {
            "scraper": stations_available,  # Based on actual test
            "notifications": is_firebase_enabled(),
            "cache": True
        },
        "uptime_seconds": int(time.time() - startup_time)
    }
    
    return details

def cache_key(store, service):
    return f"{store}:{service}"

def get_station_name(store_id):
    """Get the real station name from store_id"""
    try:
        # Get stations data
        group_data = scraper.get_group_startup("", "1")
        estaciones = scraper.extract_stations(group_data)
        
        # Find the station with matching store_id
        for estacion in estaciones:
            if str(estacion.get('store_id')) == str(store_id):
                provincia = estacion.get('provincia', '')
                nombre = estacion.get('nombre', '')
                tipo = estacion.get('tipo', '')
                return f"{provincia} - {nombre} ({tipo})"
        
        # Fallback if not found
        return f"Estación {store_id}"
    except Exception as e:
        print(f"Error getting station name for {store_id}: {e}")
        return f"Estación {store_id}"

def get_cached_slots(store, service):
    key = cache_key(store, service)
    with slots_cache_lock:
        entry = slots_cache.get(key)
        if entry and (time.time() - entry['timestamp'] < CACHE_TTL):
            return entry['data']
    return None

def detect_new_appointments_for_users(old_data, new_data, store, service):
    """Detects new appointments and determines which users should be notified"""
    if not new_data:
        return []
    
    from notifier import registered_tokens
    
    # Get all users who have this station in their favorites
    interested_users = []
    store_str = str(store)
    
    for token, token_data in registered_tokens.items():
        favoritos = token_data.get("favoritos", [])
        favoritos_str = [str(f) for f in favoritos] if favoritos else []
        if store_str in favoritos_str:
            user_id = token_data.get("user_id")
            interested_users.append({
                'token': token,
                'user_id': user_id,
                'last_seen_appointments': token_data.get(f"last_seen_{store}_{service}", [])
            })
    
    if not interested_users:
        print(f"No users interested in store {store}, service {service}")
        return []
    
    print(f"Found {len(interested_users)} users interested in store {store}, service {service}")
    
    # Create current appointments set
    current_appointments = set()
    current_appointments_list = []
    for item in new_data:
        if isinstance(item, dict) and 'fecha' in item and 'hora' in item:
            appointment_id = f"{item['fecha']}_{item['hora']}"
            current_appointments.add(appointment_id)
            current_appointments_list.append(appointment_id)
    
    # Check each user individually
    notifications_to_send = []
    estacion_nombre = None
    
    for user in interested_users:
        user_last_seen = set(user['last_seen_appointments'])
        user_new_appointments = current_appointments - user_last_seen
        
        if user_new_appointments:
            if estacion_nombre is None:
                estacion_nombre = get_station_name(store)
            
            print(f"User {user['user_id']} has {len(user_new_appointments)} new appointments")
            
            # Create notification data for this user
            for item in new_data:
                if isinstance(item, dict) and 'fecha' in item and 'hora' in item:
                    appointment_id = f"{item['fecha']}_{item['hora']}"
                    if appointment_id in user_new_appointments:
                        notifications_to_send.append({
                            'token': user['token'],
                            'user_id': user['user_id'],
                            'store_id': int(store),
                            'estacion_nombre': estacion_nombre,
                            'fecha': item['fecha'],
                            'hora': item['hora']
                        })
        
        # Update user's last seen appointments
        from notifier import update_user_last_seen_appointments
        update_user_last_seen_appointments(user['token'], store, service, current_appointments_list)
    
    return notifications_to_send

def set_cached_slots(store, service, data):
    key = cache_key(store, service)
    
    with slots_cache_lock:
        # Check if there are new appointments for specific users
        old_data = slots_cache.get(key, {}).get('data', [])
        user_notifications = detect_new_appointments_for_users(old_data, data, store, service)
        
        # Update cache
        slots_cache[key] = {'data': data, 'timestamp': time.time()}
        
        # Send personalized notifications
        if user_notifications:
            print(f"Sending {len(user_notifications)} personalized notifications")
            for notification in user_notifications:
                send_new_appointment_notification(
                    notification['estacion_nombre'],
                    notification['fecha'], 
                    notification['hora'],
                    specific_token=notification['token'],
                    store_id=notification['store_id']
                )

# Background thread to refresh cache periodically
def background_cache_refresher():
    """Updates available appointments cache in background respectfully"""
    while True:
        try:
            # Get all favorite stations from registered tokens
            from notifier import registered_tokens
            favorite_stations = set()
            
            for token_data in registered_tokens.values():
                favoritos = token_data.get("favoritos", [])
                if favoritos:
                    favorite_stations.update(favoritos)
            
            print(f"Found {len(favorite_stations)} favorite stations from registered users: {list(favorite_stations)}")
            
            # Add favorite stations to cache monitoring with common services
            # Common service IDs for different vehicle types
            common_services = ["227", "228", "229"]  # Turismo diesel, gasolina, eléctrico
            
            for station in favorite_stations:
                for service in common_services:
                    key = cache_key(station, service)
                    if key not in slots_cache:
                        print(f"Adding favorite station {station} service {service} to monitoring")
                        # Initialize with empty data so it gets refreshed
                        with slots_cache_lock:
                            slots_cache[key] = {'data': [], 'timestamp': 0}
            
            # Refresh all keys that are now in cache
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
                            
                            # Delay between requests to be respectful
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
    """Gets available services for a specific ITV station"""
    print(f"Getting services for station {store_id}...")
    
    # Use the new get_startup method
    startup_data = scraper.get_startup("", store_id)
    
    categories = startup_data.get('categoriesServices', {})
    print(f"[DEBUG] categoriesServices found: {len(categories)} categories")
    
    servicios = []
    for cat_key, cat in categories.items():
        cat_name = cat.get('name', 'Unknown')
        services = cat.get('services', {})
        
        for serv_key, serv in services.items():
            service_id = serv.get('id')
            nombre = serv.get('name')
            if nombre and service_id:
                servicios.append({
                    'nombre': nombre, 
                    'service': service_id, 
                    'categoria': cat_name
                })
    
    print(f"[DEBUG] Extracted {len(servicios)} services for station {store_id}")
    return {"servicios": servicios}

# Endpoint para registrar el token FCM
@app.post("/register-token")
async def register_token_endpoint(request: Request):
    """Registra un token FCM junto con user_id y favoritos"""
    try:
        data = await request.json()
        token = data.get("token")
        user_id = data.get("user_id")
        favoritos = data.get("favoritos")  # Debe ser lista de estaciones favoritas
        if not token:
            return JSONResponse({"error": "Token is required"}, status_code=400)
        # Validar favoritos como lista
        if favoritos is not None and not isinstance(favoritos, list):
            return JSONResponse({"error": "Favoritos debe ser una lista"}, status_code=400)
        success = register_device_token(token, user_id=user_id, favoritos=favoritos)
        if success:
            return {
                "status": "success",
                "message": "Token registered successfully",
                "registered_devices": get_registered_tokens_count()
            }
        else:
            return JSONResponse({"error": "Invalid token format"}, status_code=400)
    except Exception as e:
        print(f"Error registering token: {e}")
        return JSONResponse({"error": "Failed to register token"}, status_code=500)

# Endpoint para actualizar favoritos de un token
@app.post("/update-favorites")
async def update_favorites_endpoint(request: Request):
    """Actualiza la lista de favoritos para un token específico"""
    try:
        data = await request.json()
        token = data.get("token")
        favoritos = data.get("favoritos", [])
        
        if not token:
            return JSONResponse({"error": "Token is required"}, status_code=400)
        
        # Validar favoritos como lista de enteros
        if not isinstance(favoritos, list):
            return JSONResponse({"error": "Favoritos debe ser una lista"}, status_code=400)
        
        # Convertir a enteros si vienen como strings
        try:
            favoritos = [int(f) for f in favoritos]
        except (ValueError, TypeError):
            return JSONResponse({"error": "Favoritos debe contener solo números de estación"}, status_code=400)
        
        success = register_device_token(token, favoritos=favoritos)
        if success:
            return {
                "status": "success", 
                "message": "Favorites updated successfully",
                "favoritos_count": len(favoritos),
                "favoritos": favoritos
            }
        else:
            return JSONResponse({"error": "Token not found"}, status_code=404)
            
    except Exception as e:
        print(f"Error updating favorites: {e}")
        return JSONResponse({"error": "Failed to update favorites"}, status_code=500)

@app.delete("/unregister-token")
async def unregister_token_endpoint(request: Request):
    """Remove a specific token from notifications"""
    try:
        data = await request.json()
        token = data.get("token")
        
        if not token:
            return JSONResponse({"error": "Token is required"}, status_code=400)
        
        # Remove the token
        from notifier import unregister_device_token
        removed = unregister_device_token(token)
        
        if removed:
            return {
                "status": "success", 
                "message": "Token removed successfully",
                "registered_devices": get_registered_tokens_count()
            }
        else:
            return {
                "status": "not_found",
                "message": "Token was not found in registered devices",
                "registered_devices": get_registered_tokens_count()
            }
            
    except Exception as e:
        print(f"Error unregistering token: {e}")
        return JSONResponse({"error": "Failed to unregister token"}, status_code=500)

@app.delete("/clear-all-tokens")
def clear_all_tokens_endpoint():
    """Remove ALL tokens (admin function)"""
    try:
        from notifier import clear_all_tokens
        count_before = get_registered_tokens_count()
        clear_all_tokens()
        
        return {
            "status": "success",
            "message": f"Cleared {count_before} tokens",
            "registered_devices": get_registered_tokens_count()
        }
        
    except Exception as e:
        print(f"Error clearing tokens: {e}")
        return {"error": "Failed to clear tokens"}, 500



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
async def get_fechas(request: Request, store: str, service: str, n: int = 3, force_refresh: bool = False):
    """Gets next available appointments for a station and service. Permite forzar datos frescos si se solicita."""
    print(f"Searching appointments for station {store}, service {service}")

    # Detectar si el frontend pide forzar datos frescos
    force_fresh = force_refresh
    cache_control = request.headers.get("Cache-Control", "").lower()
    if "no-cache" in cache_control or "no-store" in cache_control:
        force_fresh = True

    if not force_fresh:
        cached = get_cached_slots(store, service)
        if cached:
            print(f"Returning {len(cached[:n])} appointments from cache")
            return {"fechas_horas": cached[:n]}

    # Si se fuerza datos frescos o no hay cache
    print(f"Getting fresh data (force_fresh={force_fresh})...")
    try:
        with scraper_semaphore:
            fechas_horas = scraper.get_next_available_slots(store, service, "", n)
            set_cached_slots(store, service, fechas_horas)
            print(f"Got {len(fechas_horas)} new appointments")
            return {"fechas_horas": fechas_horas}
    except Exception as e:
        print(f"Error getting appointments: {e}")
        return {"fechas_horas": []}

# Endpoint para actualizar favoritos de un usuario
@app.post("/update-favorites")
async def update_favorites_endpoint(request: Request):
    """Actualiza los favoritos de un usuario específico"""
    try:
        data = await request.json()
        token = data.get("token")
        favoritos = data.get("favoritos")
        
        if not token:
            return JSONResponse({"error": "Token is required"}, status_code=400)
            
        if favoritos is not None and not isinstance(favoritos, list):
            return JSONResponse({"error": "Favoritos debe ser una lista"}, status_code=400)
        
        success = update_user_favorites(token, favoritos)
        if success:
            return {
                "status": "success", 
                "message": "Favorites updated successfully"
            }
        else:
            return JSONResponse({"error": "Token not found"}, status_code=404)
            
    except Exception as e:
        print(f"Error updating favorites: {e}")
        return JSONResponse({"error": "Failed to update favorites"}, status_code=500)

# Endpoint para estadísticas de notificaciones
@app.get("/notifications/stats")
def get_notification_stats():
    """Returns notification system statistics"""
    firebase_enabled = is_firebase_enabled()
    
    # Get favorite stations info
    from notifier import registered_tokens
    favorite_stations = set()
    tokens_with_favorites = 0
    
    for token_data in registered_tokens.values():
        favoritos = token_data.get("favoritos", [])
        if favoritos:
            favorite_stations.update(favoritos)
            tokens_with_favorites += 1
    
    return {
        "registered_devices": get_registered_tokens_count(),
        "tokens_with_favorites": tokens_with_favorites,
        "unique_favorite_stations": list(favorite_stations),
        "firebase_enabled": firebase_enabled,
        "cache_ttl": CACHE_TTL,
        "background_refresh_interval": BACKGROUND_REFRESH_INTERVAL,
        "cache_entries": len(slots_cache),
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
            return JSONResponse({"error": "Token is required"}, status_code=400)
        
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
            return JSONResponse({"error": "Failed to send notification"}, status_code=500)
            
    except Exception as e:
        print(f"Error sending test notification: {e}")
        return JSONResponse({"error": "Failed to send test notification"}, status_code=500)

# Endpoint para forzar actualización de favoritos
@app.post("/notifications/force-refresh")
async def force_refresh_favorites():
    """Force refresh appointments for all favorite stations"""
    try:
        from notifier import registered_tokens
        favorite_stations = set()
        
        for token_data in registered_tokens.values():
            favoritos = token_data.get("favoritos", [])
            if favoritos:
                favorite_stations.update(favoritos)
        
        if not favorite_stations:
            return {"message": "No favorite stations found", "refreshed": 0}
        
        print(f"Force refreshing {len(favorite_stations)} favorite stations...")
        
        # Common service IDs for different vehicle types
        common_services = ["227", "228", "229"]
        refreshed_count = 0
        
        for station in favorite_stations:
            for service in common_services:
                try:
                    print(f"Force refreshing station {station}, service {service}")
                    data = scraper.get_next_available_slots(station, service, "", 10)
                    set_cached_slots(station, service, data)
                    refreshed_count += 1
                    time.sleep(2)  # Small delay to be respectful
                except Exception as e:
                    print(f"Error refreshing {station}:{service}: {e}")
        
        return {
            "message": f"Force refresh completed",
            "favorite_stations": list(favorite_stations),
            "refreshed_combinations": refreshed_count
        }
        
    except Exception as e:
        print(f"Error in force refresh: {e}")
        return JSONResponse({"error": "Failed to force refresh"}, status_code=500)

# Endpoint para limpiar historial de citas vistas (útil para testing)
@app.post("/notifications/clear-user-history")
async def clear_user_history(request: Request):
    """Clear a user's appointment history to force notifications"""
    try:
        data = await request.json()
        token = data.get("token")
        
        if not token:
            return JSONResponse({"error": "Token is required"}, status_code=400)
        
        from notifier import registered_tokens, save_tokens_data
        
        if token not in registered_tokens:
            return JSONResponse({"error": "Token not found"}, status_code=404)
        
        # Remove all last_seen_* keys for this user
        user_data = registered_tokens[token]
        keys_to_remove = [key for key in user_data.keys() if key.startswith("last_seen_")]
        
        for key in keys_to_remove:
            del user_data[key]
        
        save_tokens_data()
        
        return {
            "message": f"Cleared {len(keys_to_remove)} appointment history entries for user",
            "cleared_keys": keys_to_remove
        }
        
    except Exception as e:
        print(f"Error clearing user history: {e}")
        return JSONResponse({"error": "Failed to clear user history"}, status_code=500)



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

