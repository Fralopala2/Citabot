

# Citabot

Citabot is a Flutter app for Android that automatically searches for available appointments in Spanish government services such as ITV and NIA renewal. The app communicates with a Python (FastAPI) backend that performs the search and sends push notifications.

## Features
- Modern and attractive interface
- Buttons to search for ITV and NIA appointments
- Push notifications via Firebase Cloud Messaging (FCM)
- FastAPI backend with simulated endpoints for testing

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
- `GET /cita-itv` — Returns simulated ITV appointments
- `GET /cita-nia` — Returns simulated NIA appointments

## Technical Details
- The backend responds in JSON format with a list of appointments.
- The app displays results in dialog boxes.
- The FCM token is sent automatically to the backend when the app starts.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

Commercial use is strictly prohibited without prior written permission from the author.

## Contact

Created by Paco (@Fralopala2)  
Feel free to open issues or suggest improvements via GitHub.