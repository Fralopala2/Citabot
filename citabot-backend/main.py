import json
import threading
import time
import os
from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from notifier import register_device_token, send_new_appointment_notification, get_registered_tokens_count, is_firebase_enabled
from scraper_sitval import SitValScraper

# Server startup time for health checks
startup_time = time.time()

# File for persistent storage of testers data
TESTERS_DATA_FILE = "testers_data.json"

def load_testers_data():
    """Load testers data from persistent storage"""
    try:
        if os.path.exists(TESTERS_DATA_FILE):
            with open(TESTERS_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 Loaded {len(data)} testers from persistent storage")
                return data
    except Exception as e:
        print(f"❌ Error loading testers data: {e}")
    
    print("📂 No existing testers data found, starting fresh")
    return {}

def save_testers_data(installations_dict):
    """Save tester data to persistent storage"""
    try:
        with open(TESTERS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(installations_dict, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(installations_dict)} testers to persistent storage")
        return True
    except Exception as e:
        print(f"❌ Error saving testers data: {e}")
        return False

def clear_dashboard():
    """Borra todos los testers registrados y reinicia el contador de instalaciones"""
    empty_dashboard = {
        "testers": [],
        "total_installations": 0
    }
    save_testers_data(empty_dashboard)
    print("🧹 Dashboard limpiado - todos los testers eliminados")
    return empty_dashboard

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

# Initialize persistent testers data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize server with persistent data"""
    # Load testers data from file
    if not hasattr(app.state, 'installations'):
        app.state.installations = load_testers_data()
    
    print("🚀 Citabot server started with persistent testers data")

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
            return {"error": "Token is required"}, 400
        # Validar favoritos como lista
        if favoritos is not None and not isinstance(favoritos, list):
            return {"error": "Favoritos debe ser una lista"}, 400
        success = register_device_token(token, user_id=user_id, favoritos=favoritos)
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

@app.delete("/unregister-token")
async def unregister_token_endpoint(request: Request):
    """Remove a specific token from notifications"""
    try:
        data = await request.json()
        token = data.get("token")
        
        if not token:
            return {"error": "Token is required"}, 400
        
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
        return {"error": "Failed to unregister token"}, 500

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


# Installation tracking endpoints
@app.post("/track-installation")
async def track_installation(request: Request):
    """Track app installation by a tester"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        platform = data.get("platform", "unknown")
        app_version = data.get("app_version", "unknown")
        timestamp = data.get("timestamp")
        
        if not user_id:
            return {"error": "user_id is required"}, 400
        
        # Store installation data
        installation_data = {
            "user_id": user_id,
            "platform": platform,
            "app_version": app_version,
            "timestamp": timestamp,
            "event_type": "install",
            "last_seen": timestamp
        }
        
        # Add to installations tracking with persistent storage
        if not hasattr(app.state, 'installations'):
            app.state.installations = load_testers_data()
        
        app.state.installations[user_id] = installation_data
        
        # Save to persistent storage
        save_testers_data(app.state.installations)
        
        print(f"📱 Installation tracked: User {user_id} on {platform} v{app_version}")
        
        return {
            "status": "success",
            "message": "Installation tracked successfully",
            "user_id": user_id,
            "total_installations": len(app.state.installations)
        }
        
    except Exception as e:
        print(f"Error tracking installation: {e}")
        return {"error": "Failed to track installation"}, 500

@app.post("/track-usage")
async def track_usage(request: Request):
    """Track app usage (daily heartbeat)"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        timestamp = data.get("timestamp")
        
        if not user_id:
            return {"error": "user_id is required"}, 400
        
        # Update last seen timestamp
        if hasattr(app.state, 'installations') and user_id in app.state.installations:
            app.state.installations[user_id]["last_seen"] = timestamp
            
            # Save to persistent storage
            save_testers_data(app.state.installations)
            
            print(f"📊 Usage tracked: User {user_id}")
            
            return {
                "status": "success", 
                "message": "Usage tracked successfully"
            }
        else:
            return {"error": "User not found in installations"}, 404
        
    except Exception as e:
        print(f"Error tracking usage: {e}")
        return {"error": "Failed to track usage"}, 500

@app.get("/admin/testers")
def get_testers_status():
    """Get installation status of all testers (admin endpoint)"""
    try:
        if not hasattr(app.state, 'installations'):
            app.state.installations = load_testers_data()
        
        testers = []
        for user_id, data in app.state.installations.items():
            testers.append({
                "user_id": user_id,
                "platform": data.get("platform", "unknown"),
                "app_version": data.get("app_version", "unknown"),
                "install_date": data.get("timestamp"),
                "last_seen": data.get("last_seen"),
                "days_since_install": _calculate_days_since(data.get("timestamp")),
                "days_since_last_seen": _calculate_days_since(data.get("last_seen"))
            })
        
        # Sort by install date (newest first)
        testers.sort(key=lambda x: x.get("install_date", ""), reverse=True)
        
        return {
            "total_testers": len(testers),
            "active_installations": len([t for t in testers if t["days_since_last_seen"] <= 1]),
            "total_usage_events": sum(1 for t in testers if t.get("last_seen")),
            "testers": testers
        }
        
    except Exception as e:
        print(f"Error getting testers status: {e}")
        return {"error": "Failed to get testers status"}, 500

@app.get("/admin/dashboard")
def get_testers_dashboard():
    """HTML dashboard for testers tracking"""

@app.get("/admin/clear-dashboard")
async def admin_clear_dashboard():
    """Limpia el dashboard eliminando todos los testers registrados"""
    cleared_data = clear_dashboard()
    app.state.installations = cleared_data
    return {"message": "Dashboard limpiado correctamente", "data": cleared_data}
    try:
        if not hasattr(app.state, 'installations'):
            app.state.installations = load_testers_data()
        
        testers = []
        for user_id, data in app.state.installations.items():
            testers.append({
                "user_id": user_id,
                "platform": data.get("platform", "unknown"),
                "app_version": data.get("app_version", "unknown"),
                "install_date": data.get("timestamp"),
                "last_seen": data.get("last_seen"),
                "days_since_install": _calculate_days_since(data.get("timestamp")),
                "days_since_last_seen": _calculate_days_since(data.get("last_seen"))
            })
        
        # Sort by install date (newest first)
        testers.sort(key=lambda x: x.get("install_date", ""), reverse=True)
        
        total_testers = len(testers)
        active_testers = len([t for t in testers if t["days_since_last_seen"] <= 1])
        usage_events = sum(1 for t in testers if t.get("last_seen"))
        
        # Generate HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Citabot - Panel de Testers</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .stats {{ display: flex; justify-content: space-around; margin-bottom: 30px; }}
                .stat-card {{ background: #007bff; color: white; padding: 20px; border-radius: 8px; text-align: center; min-width: 150px; }}
                .stat-number {{ font-size: 2em; font-weight: bold; }}
                .stat-label {{ font-size: 0.9em; }}
                .table-container {{ overflow-x: auto; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                .user-id {{ font-family: monospace; font-size: 0.85em; }}
                .active {{ color: #28a745; font-weight: bold; }}
                .inactive {{ color: #dc3545; }}
                .refresh-btn {{ background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 20px; }}
                .refresh-btn:hover {{ background: #218838; }}
                .progress {{ background: #e9ecef; height: 20px; border-radius: 10px; margin: 10px 0; }}
                .progress-bar {{ background: #28a745; height: 100%; border-radius: 10px; text-align: center; line-height: 20px; color: white; font-size: 12px; }}
            </style>
            <script>
                function refreshPage() {{
                    location.reload();
                }}
                setTimeout(refreshPage, 30000); // Auto-refresh every 30 seconds
            </script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 Citabot - Panel de Testers</h1>
                    <p>Monitoreo de instalaciones para Google Play</p>
                    <button class="refresh-btn" onclick="refreshPage()">🔄 Actualizar</button>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{total_testers}</div>
                        <div class="stat-label">Total Testers</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{active_testers}</div>
                        <div class="stat-label">Activos (24h)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{usage_events}</div>
                        <div class="stat-label">Eventos de Uso</div>
                    </div>
                </div>
                
                <div class="progress">
                    <div class="progress-bar" style="width: {min(total_testers/12*100, 100)}%;">
                        {total_testers}/12 testers ({min(total_testers/12*100, 100):.0f}%)
                    </div>
                </div>
                
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>User ID</th>
                                <th>Plataforma</th>
                                <th>Versión</th>
                                <th>Fecha Instalación</th>
                                <th>Último Uso</th>
                                <th>Días Activo</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for i, tester in enumerate(testers, 1):
            user_id_short = tester["user_id"][:20] + "..." if len(tester["user_id"]) > 23 else tester["user_id"]
            install_date = tester.get("install_date", "").split("T")[0] if tester.get("install_date") else "N/A"
            last_seen_date = tester.get("last_seen", "").split("T")[0] if tester.get("last_seen") else "N/A"
            days_since_last = tester.get("days_since_last_seen", 999)
            status_class = "active" if days_since_last <= 1 else "inactive"
            status_text = "🟢 Activo" if days_since_last <= 1 else "🔴 Inactivo"
            
            html_content += f"""
                            <tr>
                                <td>{i}</td>
                                <td class="user-id">{user_id_short}</td>
                                <td>{tester.get("platform", "N/A").title()}</td>
                                <td>{tester.get("app_version", "N/A")}</td>
                                <td>{install_date}</td>
                                <td>{last_seen_date}</td>
                                <td>{tester.get("days_since_install", "N/A")}</td>
                                <td class="{status_class}">{status_text}</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
                
                <div style="margin-top: 30px; text-align: center; color: #666;">
                    <p>🎯 <strong>Objetivo:</strong> 12 testers activos durante 14 días para Google Play</p>
                    <p>📊 <strong>API JSON:</strong> <a href="/admin/testers">Ver datos en formato JSON</a></p>
                    <p>🔄 Esta página se actualiza automáticamente cada 30 segundos</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        print(f"Error generating dashboard: {e}")
        return {"error": "Failed to generate dashboard"}, 500

def _calculate_days_since(timestamp_str):
    """Calculate days since a timestamp"""
    if not timestamp_str:
        return None
    
    try:
        from datetime import datetime
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timestamp.tzinfo)
        return (now - timestamp).days
    except Exception:
        return None


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
from fastapi import Request

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
# Endpoint para estadísticas de notificaciones
@app.get("/notifications/stats")
def get_notification_stats():
    """Returns notification system statistics"""
    firebase_enabled = is_firebase_enabled()
    return {
        "registered_devices": get_registered_tokens_count(),
        "firebase_enabled": firebase_enabled,
        "cache_ttl": CACHE_TTL,
        "background_refresh_interval": BACKGROUND_REFRESH_INTERVAL,
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

@app.get("/admin/delete-tester")
def delete_tester(user_id: str):
    """Delete a tester by user_id (admin endpoint)"""
    try:
        if not hasattr(app.state, 'installations'):
            app.state.installations = load_testers_data()
        
        if user_id in app.state.installations:
            del app.state.installations[user_id]
            save_testers_data(app.state.installations)
            return {"status": "success", "message": f"Tester {user_id} deleted."}
        else:
            return {"status": "not_found", "message": f"Tester {user_id} not found."}, 404
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500