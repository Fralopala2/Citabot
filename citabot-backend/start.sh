#!/bin/bash
# Start script for Render deployment
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}