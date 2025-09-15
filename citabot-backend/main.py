import json
import threading
import time
import os
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from notifier import send_notification
from scraper_sitval import SitValScraper



scraper = SitValScraper()
app = FastAPI(
    title="Citabot API",
    description="API para consultar citas ITV en tiempo real",
    version="1.0.0"
)

# Configure CORS for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

def set_cached_slots(store, service, data):
    key = cache_key(store, service)
    with slots_cache_lock:
        slots_cache[key] = {'data': data, 'timestamp': time.time()}

# Background thread to refresh cache periodically
def background_cache_refresher():
    """Updates available appointments cache in background respectfully"""
    while True:
        try:
            # Refresh all keys that are already in cache
            with slots_cache_lock:
                keys = list(slots_cache.keys())
            
            if keys:
                print(f"🔄 Refreshing cache for {len(keys)} station-service combinations...")
                
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
                        print(f"   ❌ Error refreshing cache for {key}: {e}")
                
                print("✅ Cache refreshed completely")
            else:
                print("📭 No cache entries to refresh")
                
        except Exception as e:
            print(f"❌ Error in background_cache_refresher: {e}")
        
        # Wait for configured interval before next refresh
        time.sleep(BACKGROUND_REFRESH_INTERVAL)

threading.Thread(target=background_cache_refresher, daemon=True).start()

# Endpoint to get available services by station
@app.get("/itv/servicios")
def get_servicios(store_id: str):
    instance_code = scraper.get_instance_code_robust(store_id)
    group_data = scraper.get_group_startup(instance_code, store_id)
    # Buscar la estación por store_id y extraer servicios reales desde params
    for prov in group_data.get('groups', {}).values():
        for level2 in prov.get('level2', {}).values():
            for store in level2.get('stores', {}).values():
                if str(store.get('store')) == str(store_id):
                    print(f"[DEBUG] store encontrado para store_id={store_id}: {json.dumps(store, ensure_ascii=False)[:1000]}")
                    params = store.get('params') or []
                    print(f"[DEBUG] params extraído: {json.dumps(params, ensure_ascii=False)[:2000]}")
                    servicios = []
                    for param in params:
                        # Solo servicios que sean de tipo 'Servicio' (type == "-2")
                        if str(param.get('store')) == str(store_id) and param.get('type') == "-2":
                            nombre = param.get('name')
                            service_id = param.get('id')
                            if nombre and service_id:
                                servicios.append({'nombre': nombre, 'service': service_id})
                    print(f"[DEBUG] servicios extraídos de params: {servicios}")
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
    print(f"🔍 Searching appointments for station {store}, service {service}")
    
    # Try to get from cache first
    cached = get_cached_slots(store, service)
    if cached:
        print(f"📦 Returning {len(cached[:n])} appointments from cache")
        return {"fechas_horas": cached[:n]}
    
    # If not in cache, get with concurrency control
    print(f"🌐 No cache, getting fresh data...")
    
    try:
        # Use semaphore to limit concurrent requests
        with scraper_semaphore:
            # Use empty instanceCode as it works perfectly
            fechas_horas = scraper.get_next_available_slots(store, service, "", n)
            set_cached_slots(store, service, fechas_horas)
            
            print(f"✅ Got {len(fechas_horas)} new appointments")
            return {"fechas_horas": fechas_horas}
            
    except Exception as e:
        print(f"❌ Error getting appointments: {e}")
        # Return empty array in case of error
        return {"fechas_horas": []}
# Endpoint to register FCM token
@app.post("/register-token")
async def register_token(request: Request):
    data = await request.json()
    token = data.get("token")
    print(f"FCM Token registered: {token}")
    return {"message": "Token registered successfully"}

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