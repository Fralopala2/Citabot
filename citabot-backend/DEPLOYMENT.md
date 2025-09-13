# 🚀 Citabot Backend Deployment Guide

## Render Deployment

### Prerequisites
- Render account
- GitHub repository with the backend code

### Deployment Steps

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Prepare backend for Render deployment"
   git push origin main
   ```

2. **Create New Web Service in Render**:
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select the repository with citabot-backend

3. **Configure Service**:
   - **Name**: `citabot-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free` (for testing)

4. **Environment Variables** (Optional):
   - `PYTHON_VERSION`: `3.11.0`

5. **Deploy**:
   - Click "Create Web Service"
   - Wait for deployment to complete

### After Deployment

Your API will be available at: `https://citabot-backend.onrender.com`

### Test Endpoints

- Health check: `GET /`
- Get stations: `GET /itv/estaciones`
- Get services: `GET /itv/servicios?store_id=1`
- Get appointments: `GET /itv/fechas?store=1&service=443&n=5`

### Update Mobile App

Update the API URL in your Flutter app from:
```dart
'http://10.0.2.2:8000/itv/estaciones'
```

To:
```dart
'https://citabot-backend.onrender.com/itv/estaciones'
```

## Features

✅ **Real-time ITV appointment scraping**
✅ **Station-specific data isolation**
✅ **Intelligent caching system**
✅ **Rate limiting to avoid bans**
✅ **CORS enabled for web apps**
✅ **Health check endpoint**
✅ **Background cache refresh**

## API Documentation

Once deployed, visit: `https://citabot-backend.onrender.com/docs`