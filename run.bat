@echo off
REM Navigate to backend folder
cd citabot-backend

REM Activate virtual environment
call venv\Scripts\activate

REM Run FastAPI server with auto-reload
uvicorn main:app --reload
