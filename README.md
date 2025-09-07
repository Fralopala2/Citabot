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
- Modular backend ready for expansion (more services, cities, etc.)

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

## Technical Details

- The backend uses robust scraping logic to extract real appointment data from the official SITVAL system
- InstanceCode extraction is handled automatically for reliable results
- All endpoints respond in JSON format
- The app displays results in dialogs and interactive screens
- FCM token is sent automatically to the backend when the app starts
- Modular backend design allows for easy expansion and maintenance

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

Commercial use is strictly prohibited without prior written permission from the author.

## Contact

Created by Paco (@Fralopala2)
Feel free to open issues or suggest improvements via GitHub.
