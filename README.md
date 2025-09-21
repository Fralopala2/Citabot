<p align="center">
  <img width="300" height="300" alt="citabot" src="https://github.com/user-attachments/assets/174c87ad-1ee3-455e-871a-54fb968bdf37" />
</p>

# Citabot

Citabot is a Flutter app for Android that automates the search for available appointments in services, including ITV (vehicle inspection). The app connects to a robust Python FastAPI backend that performs real-time scraping, delivers accurate appointment data, and sends **automatic push notifications** when new appointments become available.

## ✨ Key Features

### 🔔 **Automatic Push Notifications**

- **Real-time monitoring**: Backend checks for new free appointments every 1 hour
- **Firebase Cloud Messaging (FCM)**: Notifications work even when app is closed
- **Smart detection**: Only notifies when genuinely new appointments appear
- **Works 24/7**: No need to keep the app open or check manually

### 📱 **Modern User Experience**

- Clean, intuitive, and responsive Material Design interface
- Custom loading indicators with animations and informative messages
- Enhanced error handling with user-friendly feedback
- Smooth navigation and interactive elements

### 🎯 **Smart Appointment Search**

- Search for **real ITV appointments** by province, station, and service type
- **Favorites system**: Save preferred stations for quick access
- **Bulk search**: Find earliest available appointment across all favorite stations
- **Date filtering**: Automatically excludes past dates from results
- Real-time availability with accurate dates, times, and prices

### 🛡️ **Security & Performance**

- **Restricted CORS policy**: Backend only accepts requests from known domains
- **Rate limiting**: Respectful scraping to avoid service disruption
- **Intelligent caching**: 30-minute cache with background refresh
- **Environment-based configuration**: Separate settings for development and production

## Requirements

- Flutter 3.x
- Android Studio or Android emulator API 33/34+
- Python 3.9+
- FastAPI and Uvicorn for the backend

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Fralopala2/Citabot.git
   ```
2. Install Flutter dependencies:
   ```
   cd citabot_app
   flutter pub get
   ```
3. Install backend dependencies:
   ```
   cd citabot-backend
   pip install -r requirements.txt
   ```

## 🚀 Quick Start

### For End Users

1. **Download and install** the APK on your Android device
2. **Open the app** - it will automatically register for notifications
3. **Add favorite stations** you want to monitor
4. **Receive automatic notifications** when new appointments become available

### For Developers

#### Backend Development

1. Configure environment:
   ```bash
   cd citabot-backend
   cp .env.example .env
   cp firebase-service-account.json.example firebase-service-account.json
   # Edit both files with your Firebase credentials
   ```
2. Start the backend:
   ```bash
   uvicorn main:app --reload
   ```
   Backend available at `http://127.0.0.1:8000`

#### Android App Development

1. Configure Firebase:
   ```bash
   cd citabot_app/android/app
   cp google-services.json.example google-services.json
   # Edit with your Firebase Android configuration
   ```
2. Run the app:
   ```bash
   cd citabot_app
   flutter run
   ```

## Project Structure

- `citabot_app/` — Flutter source code (Android only)
- `citabot-backend/` — Python FastAPI backend

## 🚀 Backend Endpoints

### Core Functionality

- `GET /itv/estaciones` — Returns all real ITV stations and provinces
- `GET /itv/servicios` — Returns available services for a specific station
- `GET /itv/fechas` — Returns next available dates and times for ITV appointments
- `GET /cita-nia` — Returns simulated NIA appointments

### Push Notifications

- `POST /register-token` — Registers FCM device token for notifications
- `POST /notifications/test` — Test endpoint to send notification to specific token
- `GET /notifications/stats` — Returns notification system statistics

### System Monitoring

- `GET /cache/status` — Returns cache status and refresh intervals
- `POST /cache/clear` — Manually clears all cached data
- `GET /debug/fechas` — Debug endpoint for raw scraper data
- `GET /` — Health check endpoint

## 🔧 Configuration

### ⚠️ IMPORTANT: Configuration Files

**Before running the project, you must configure the sensitive files:**

#### Backend (Firebase and environment variables):

```bash
cd citabot-backend
cp .env.example .env
cp firebase-service-account.json.example firebase-service-account.json
```

Then edit both files with your real Firebase credentials.

#### Flutter App (Google Services):

```bash
cd citabot_app/android/app
cp google-services.json.example google-services.json
```

Edit the file with your Firebase configuration for Android.

### Environment Variables

The `.env` file in `citabot-backend/` should contain:

```env
# Firebase Configuration (for push notifications)
FIREBASE_CONFIG={"type":"service_account","project_id":"your-project",...}

# Cache Configuration (optional)
CACHE_TTL=1800  # 30 minutes cache duration
BACKGROUND_REFRESH_INTERVAL=1800  # 30 minutes between automatic checks
MAX_CONCURRENT_REQUESTS=2  # Limit concurrent scraping requests
REQUEST_DELAY=5.0  # Seconds between requests to be respectful

# Environment
ENVIRONMENT=production  # or "development"
```

### Firebase Setup

1. **Create Firebase project** at [Firebase Console](https://console.firebase.google.com/)
2. **Enable Cloud Messaging** in your project
3. **Generate service account key**:
   - Go to Project Settings → Service Accounts
   - Click "Generate new private key"
   - Download the JSON file
4. **Configure environment**:
   - For local development: Save as `firebase-service-account.json`
   - For production (Render): Set `FIREBASE_CONFIG` environment variable with the JSON content

## 🔧 Technical Details

### Backend Architecture

- **Robust scraping engine**: Extracts real appointment data from official SITVAL system
- **Automatic instanceCode extraction**: Handles session management reliably
- **Intelligent caching**: 30-minute TTL with background refresh every 30 minutes
- **Rate limiting**: Maximum 2 concurrent requests, 5-second delays to prevent bans
- **CORS security**: Restricted to specific domains, limited HTTP methods
- **Environment-aware**: Different configurations for development vs production

### Push Notification System

- **Firebase Cloud Messaging (FCM)**: Industry-standard push notification service
- **Automatic token registration**: Devices register themselves when app starts
- **Background monitoring**: Server continuously monitors for new appointments
- **Smart detection**: Compares current vs cached data to identify new appointments
- **Token cleanup**: Automatically removes invalid/expired tokens
- **Works offline**: Notifications delivered even when app is closed

### Mobile App Features

- **Custom UI components**: Loading indicators with animations and overlays
- **Date filtering**: Automatically excludes past dates from search results
- **Favorites management**: Local storage for preferred stations
- **Error handling**: Comprehensive error messages and recovery options
- **Material Design**: Modern Android UI following Google's design guidelines

### Deployment

- **Backend**: Deployed on Render with automatic GitHub integration
- **Database**: In-memory caching with periodic refresh (no external DB required)
- **Security**: Environment variables for sensitive data, .gitignore for credentials
- **Monitoring**: Built-in endpoints for system health and cache status

## 🚀 Production Deployment

### Backend (Render)

The backend is deployed at `https://citabot.onrender.com` with:

- Automatic deployment from GitHub main branch
- Environment variables configured in Render dashboard
- Firebase credentials stored securely as environment variables
- CORS configured for production domains

### Mobile App Distribution

1. **Build release APK**:
   ```bash
   cd citabot_app
   flutter build apk --release
   ```
2. **APK location**: `citabot_app/build/app/outputs/flutter-apk/app-release.apk`
3. **Installation**: Transfer APK to Android device and install

### Monitoring Production

- **Health check**: `GET https://citabot.onrender.com/`
- **Notification stats**: `GET https://citabot.onrender.com/notifications/stats`
- **Cache status**: `GET https://citabot.onrender.com/cache/status`

## 🌟 Advanced Features

### Favorites System

- **Save preferred stations**: Quick access to your most-used ITV locations
- **Bulk search capability**: Find earliest appointment across all favorite stations in one search
- **Smart comparison**: Automatically shows the first available slot among all favorites
- **Local storage**: Favorites persist on your device for fast access
- **Dedicated management**: Clean interface for adding/removing favorite stations

### Automatic Notifications

- **Set and forget**: Add stations to favorites and receive automatic notifications
- **Real-time monitoring**: Backend checks your favorite stations every 30 minutes
- **New appointment alerts**: Get notified immediately when new slots become available
- **No manual checking**: System works 24/7 without user intervention
- **Multiple stations**: Monitor several locations simultaneously

### User Experience Enhancements

- **Loading animations**: Custom indicators with rotating icons and overlays
- **Informative messages**: Clear feedback during data fetching and cache refresh
- **Error recovery**: Helpful messages and retry options when searches fail
- **Date validation**: Automatic filtering of past dates from results
- **Responsive design**: Optimized for different screen sizes and orientations

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

Commercial use is strictly prohibited without prior written permission from the author.

## Contact

Created by Paco (@Fralopala2)
Feel free to open issues or suggest improvements via GitHub.
