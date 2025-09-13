#!/usr/bin/env python3
"""
Configuración del sistema de caché para evitar baneos de Cloudflare
"""

import os
from typing import Dict, Any

class CacheConfig:
    """Configuración centralizada del sistema de caché"""
    
    # Configuración de caché (en segundos)
    CACHE_TTL = int(os.getenv('CACHE_TTL', 1800))  # 30 minutos por defecto
    BACKGROUND_REFRESH_INTERVAL = int(os.getenv('BACKGROUND_REFRESH_INTERVAL', 900))  # 15 minutos
    
    # Configuración de rate limiting para evitar baneos
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', 2))  # Máximo 2 requests simultáneos
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', 3.0))  # 3 segundos entre requests
    
    # Configuración de reintentos
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', 5.0))  # 5 segundos entre reintentos
    
    # Configuración de horarios de scraping (para ser más respetuosos)
    SCRAPING_HOURS_START = int(os.getenv('SCRAPING_HOURS_START', 7))  # 7 AM
    SCRAPING_HOURS_END = int(os.getenv('SCRAPING_HOURS_END', 22))  # 10 PM
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Devuelve toda la configuración como diccionario"""
        return {
            'cache_ttl_minutes': cls.CACHE_TTL / 60,
            'background_refresh_interval_minutes': cls.BACKGROUND_REFRESH_INTERVAL / 60,
            'max_concurrent_requests': cls.MAX_CONCURRENT_REQUESTS,
            'request_delay_seconds': cls.REQUEST_DELAY,
            'max_retries': cls.MAX_RETRIES,
            'retry_delay_seconds': cls.RETRY_DELAY,
            'scraping_hours': f"{cls.SCRAPING_HOURS_START}:00 - {cls.SCRAPING_HOURS_END}:00"
        }
    
    @classmethod
    def is_scraping_allowed(cls) -> bool:
        """Verifica si está permitido hacer scraping en el horario actual"""
        from datetime import datetime
        current_hour = datetime.now().hour
        return cls.SCRAPING_HOURS_START <= current_hour <= cls.SCRAPING_HOURS_END
    
    @classmethod
    def print_config(cls):
        """Imprime la configuración actual"""
        config = cls.get_config()
        print("🔧 Configuración del sistema de caché:")
        for key, value in config.items():
            print(f"   {key}: {value}")

# Configuraciones predefinidas para diferentes entornos
PRODUCTION_CONFIG = {
    'CACHE_TTL': 3600,  # 1 hora en producción
    'BACKGROUND_REFRESH_INTERVAL': 1800,  # 30 minutos
    'MAX_CONCURRENT_REQUESTS': 1,  # Muy conservador en producción
    'REQUEST_DELAY': 5.0,  # 5 segundos entre requests
}

DEVELOPMENT_CONFIG = {
    'CACHE_TTL': 900,  # 15 minutos en desarrollo
    'BACKGROUND_REFRESH_INTERVAL': 600,  # 10 minutos
    'MAX_CONCURRENT_REQUESTS': 2,
    'REQUEST_DELAY': 2.0,  # 2 segundos en desarrollo
}

def apply_config(config_name: str = 'development'):
    """Aplica una configuración predefinida"""
    configs = {
        'production': PRODUCTION_CONFIG,
        'development': DEVELOPMENT_CONFIG
    }
    
    if config_name in configs:
        config = configs[config_name]
        for key, value in config.items():
            os.environ[key] = str(value)
        print(f"✅ Configuración '{config_name}' aplicada")
    else:
        print(f"❌ Configuración '{config_name}' no encontrada")

if __name__ == "__main__":
    CacheConfig.print_config()