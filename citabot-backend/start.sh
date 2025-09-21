#!/bin/bash
# Start script for Render deployment

# Inicializar archivos necesarios
python3 init_deployment.py

# Iniciar el servidor
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}