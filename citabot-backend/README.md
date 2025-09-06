# CITABOT Backend

This is a personal backend service that monitors appointment availability on Spain's official extranjería website. When a slot becomes available, it sends a push notification to your mobile app.

## 🚀 Features

- Scrapes the official appointment website using Selenium
- Sends push notifications via Firebase Cloud Messaging (FCM)
- Built with FastAPI for easy API integration
- Modular structure for future expansion (more cities, procedures, etc.)

## 🧰 Technologies Used

- Python 3.10+
- FastAPI
- Selenium
- Firebase Cloud Messaging
- Uvicorn (for running the API server)

## 📦 Project Structure

```
citabot-backend/
├── main.py          # FastAPI app entry point
├── scraper.py       # Selenium logic to check appointment availability
├── notifier.py      # Firebase push notification logic
├── config.py        # Configuration for office/procedure (optional)
├── requirements.txt # Python dependencies
├── LICENSE          # License file (CC BY-NC 4.0)
└── README.md        # Project documentation
```

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/Fralopala2/citabot-backend.git
cd citabot-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## ▶️ Running the API

```bash
uvicorn main:app --reload
```

Then visit: `http://localhost:8000/check`  
This will trigger the scraping logic and return whether an appointment is available.

## 🔔 Firebase Setup

To enable push notifications:

1. Create a Firebase project at [https://console.firebase.google.com](https://console.firebase.google.com)
2. Get your **Server Key** and **Device Token**
3. Add them to `notifier.py` or store them securely using environment variables

## 📄 License

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

You are free to use, modify, and share this code for personal and non-commercial purposes.  
**Commercial use is strictly prohibited without prior written permission from the author.**

## 📬 Contact

Created by Paco (@Fralopala2)  
Feel free to open issues or suggest improvements via GitHub.
