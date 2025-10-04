#!/usr/bin/env python3
"""
Script para inicializar archivos necesarios en el despliegue
"""
import os
import json
import shutil

def ensure_file_from_example(filename):
    """
    Crea el archivo desde su ejemplo si no existe
    """
    if not os.path.exists(filename) and os.path.exists(f"{filename}.example"):
        print(f"📄 Creando {filename} desde ejemplo...")
        shutil.copy(f"{filename}.example", filename)
        return True
    return False

def main():
    print("🚀 Inicializando archivos para el despliegue...")
    
        # No longer creating testers tracking files as tracking was removed
    
    print("✨ Inicialización completada")

if __name__ == "__main__":
    main()