#!/usr/bin/env python3
"""
Script para verificar la configuración completa de notificaciones push de Citabot
"""

import os
import json
import requests
from pathlib import Path

def check_firebase_config():
    """Verifica la configuración de Firebase"""
    print("🔥 Verificando configuración de Firebase\n")
    
    # 1. Verificar archivo de servicio del backend
    backend_service_file = Path("citabot-backend/firebase-service-account.json")
    if backend_service_file.exists():
        print("✅ Backend: firebase-service-account.json encontrado")
        try:
            with open(backend_service_file, 'r') as f:
                config = json.load(f)
                print(f"   Project ID: {config.get('project_id', 'N/A')}")
                print(f"   Client Email: {config.get('client_email', 'N/A')[:50]}...")
        except Exception as e:
            print(f"❌ Error leyendo configuración del backend: {e}")
    else:
        print("❌ Backend: firebase-service-account.json NO encontrado")
        print("   Necesitas crearlo desde Firebase Console:")
        print("   1. Ve a Firebase Console → Tu proyecto")
        print("   2. Settings → Service accounts")
        print("   3. Generate new private key")
        print("   4. Guarda el archivo como 'citabot-backend/firebase-service-account.json'")
    
    # 2. Verificar archivo de Google Services de la app
    app_service_file = Path("citabot_app/android/app/google-services.json")
    if app_service_file.exists():
        print("✅ App Android: google-services.json encontrado")
        try:
            with open(app_service_file, 'r') as f:
                config = json.load(f)
                project_info = config.get('project_info', {})
                print(f"   Project ID: {project_info.get('project_id', 'N/A')}")
                print(f"   Project Number: {project_info.get('project_number', 'N/A')}")
        except Exception as e:
            print(f"❌ Error leyendo configuración de la app: {e}")
    else:
        print("❌ App Android: google-services.json NO encontrado")
        print("   Necesitas crearlo desde Firebase Console:")
        print("   1. Ve a Firebase Console → Tu proyecto")
        print("   2. Add app → Android")
        print("   3. Package name: com.paco.citabot")
        print("   4. Download google-services.json")
        print("   5. Guarda el archivo en 'citabot_app/android/app/google-services.json'")
    
    # 3. Verificar variable de entorno (para producción)
    firebase_config_env = os.getenv("FIREBASE_CONFIG")
    if firebase_config_env:
        print("✅ Variable FIREBASE_CONFIG encontrada (producción)")
        try:
            config = json.loads(firebase_config_env)
            print(f"   Project ID: {config.get('project_id', 'N/A')}")
        except:
            print("❌ FIREBASE_CONFIG tiene formato inválido")
    else:
        print("⚠️ Variable FIREBASE_CONFIG no encontrada (ok para desarrollo local)")

def check_dependencies():
    """Verifica las dependencias necesarias"""
    print("\n📦 Verificando dependencias\n")
    
    # Backend dependencies
    try:
        import firebase_admin
        print("✅ Backend: firebase_admin instalado")
    except ImportError:
        print("❌ Backend: firebase_admin NO instalado")
        print("   Instala con: pip install firebase-admin")
    
    try:
        import requests
        print("✅ Test script: requests instalado")
    except ImportError:
        print("❌ Test script: requests NO instalado")
        print("   Instala con: pip install requests")
    
    # Flutter dependencies (verificar pubspec.yaml)
    pubspec_file = Path("citabot_app/pubspec.yaml")
    if pubspec_file.exists():
        with open(pubspec_file, 'r') as f:
            content = f.read()
            if 'firebase_core:' in content:
                print("✅ App Flutter: firebase_core en pubspec.yaml")
            else:
                print("❌ App Flutter: firebase_core falta en pubspec.yaml")
                
            if 'firebase_messaging:' in content:
                print("✅ App Flutter: firebase_messaging en pubspec.yaml")
            else:
                print("❌ App Flutter: firebase_messaging falta en pubspec.yaml")

def check_manifest():
    """Verifica AndroidManifest.xml"""
    print("\n📱 Verificando AndroidManifest.xml\n")
    
    manifest_file = Path("citabot_app/android/app/src/main/AndroidManifest.xml")
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            content = f.read()
            
        checks = [
            ("INTERNET permission", "android.permission.INTERNET"),
            ("WAKE_LOCK permission", "android.permission.WAKE_LOCK"),
            ("Firebase Messaging Service", "FlutterFirebaseMessagingService"),
            ("MESSAGING_EVENT intent", "com.google.firebase.MESSAGING_EVENT")
        ]
        
        for check_name, check_string in checks:
            if check_string in content:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name} falta")
    else:
        print("❌ AndroidManifest.xml no encontrado")

def run_all_checks():
    """Ejecuta todas las verificaciones"""
    print("🔍 VERIFICACIÓN COMPLETA DE NOTIFICACIONES PUSH CITABOT")
    print("=" * 60)
    
    check_firebase_config()
    check_dependencies()
    check_manifest()
    
    print("\n🎯 RESUMEN DE PASOS PARA ACTIVAR NOTIFICACIONES:")
    print("\n1️⃣ CONFIGURAR FIREBASE:")
    print("   - Crear proyecto en Firebase Console")
    print("   - Descargar google-services.json para Android")
    print("   - Generar service account key para backend")
    
    print("\n2️⃣ INSTALAR DEPENDENCIAS:")
    print("   Backend: pip install firebase-admin")
    print("   Flutter: flutter pub get (ya configurado)")
    
    print("\n3️⃣ PROBAR:")
    print("   1. Compilar y instalar APK: flutter build apk --release")
    print("   2. Abrir app y copiar token FCM")
    print("   3. Probar: python test_notifications.py <token>")
    
    print("\n4️⃣ VERIFICAR FUNCIONAMIENTO AUTOMÁTICO:")
    print("   - Las notificaciones se envían cada 30 minutos automáticamente")
    print("   - Solo cuando se detectan nuevas citas disponibles")
    print("   - Funciona 24/7 sin intervención del usuario")

if __name__ == "__main__":
    run_all_checks()