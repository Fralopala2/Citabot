<p align="center">
  <img width="300" height="300" alt="citabot" src="https://github.com/user-attachments/assets/174c87ad-1ee3-455e-871a-54fb968bdf37" />
</p>


# Citabot

Citabot is a Flutter app for Android that automates the search for available appointments in Spanish government services, including ITV (vehicle inspection) and NIA (foreigner ID) renewal. The app connects to a robust Python FastAPI backend that performs real-time scraping, delivers accurate appointment data, and sends push notifications.

## Features

- Modern, attractive, and responsive user interface
- Search for real ITV appointments by province, station, and service type
- Search for NIA appointments (simulated)
- Real-time availability: shows next available dates and times for ITV appointments
- Push notifications via Firebase Cloud Messaging (FCM) when new appointments are found
- Save and manage favorite stations for quick access
- Multi-step forms for appointment search and booking
- Error handling and informative feedback for failed searches
- Backend scraping logic with robust instanceCode extraction and session management
- FastAPI backend with endpoints for stations, services, and appointments
- Simulated endpoints for NIA and test purposes
- Modular backend ready for expansion (more services, cities, etc.).

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

## Usage

### Backend
1. Start the backend:
	```
	cd citabot-backend
	uvicorn main:app --reload
	```
	The backend will be available at `http://127.0.0.1:8000`.

### Android App
1. Start the Android emulator.
2. Run the app:
	```
	cd citabot_app
	flutter run -d emulator-5554
	```

## Project Structure

- `citabot_app/` — Flutter source code (Android only)
- `citabot-backend/` — Python FastAPI backend

## Backend Endpoints

- `POST /register-token` — Registers the FCM token
- `GET /itv/estaciones` — Returns real ITV stations and provinces
- `GET /itv/servicios` — Returns available services for a station
- `GET /itv/fechas` — Returns next available dates and times for ITV appointments
- `GET /cita-nia` — Returns simulated NIA appointments

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
# Firebase Configuration
FIREBASE_SERVER_KEY=your_server_key_here
FIREBASE_DEVICE_TOKEN=your_device_token_here

# Cache Configuration (optional)
CACHE_TTL=1800  # 30 minutes
BACKGROUND_REFRESH_INTERVAL=900  # 15 minutes
MAX_CONCURRENT_REQUESTS=2
REQUEST_DELAY=3.0
```

## Technical Details

- The backend uses robust scraping logic to extract real appointment data from the official SITVAL system
- InstanceCode extraction is handled automatically for reliable results
- **Intelligent caching system** - 30 minutes TTL, rate limiting to avoid bans
- **Rate limiting** - Maximum 2 concurrent requests, 3s delay between requests
- All endpoints respond in JSON format
- The app displays results in dialogs and interactive screens
- FCM token is sent automatically to the backend when the app starts
- Modular backend design allows for easy expansion and maintenance

## Favorites and Direct Search Among Favorites

- Save and manage your favorite ITV stations for quick access.
- Group multiple stations as favorites and search for the first available date and time across all your selected favorites in a single step.
- After selecting your favorite stations, you can perform a direct search to find the earliest available appointment among them, without having to check each station individually.
- The app will show you the available times for the first station with open slots, streamlining the booking process for users who monitor several locations.
- Favorites are stored locally on your device for fast and persistent access.
- The UI provides a dedicated screen for managing favorites and launching direct searches among them.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

Commercial use is strictly prohibited without prior written permission from the author.

## Contact

Created by Paco (@Fralopala2)
Feel free to open issues or suggest improvements via GitHub.
