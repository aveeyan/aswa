import os
from pathlib import Path

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# SQLite Database configuration
DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'music_data.db')}"

# Deezer API Configuration
DEEZER_API_URL = "https://api.deezer.com"

# Application Settings
DEBUG = True
SECRET_KEY = "your-secret-key-here"  # Change this in production
PLAYLIST_NAME = "aswa Discoveries"

# Number of tracks to fetch at once
TRACKS_FETCH_COUNT = 20

# Recommendation algorithm settings
RECOMMENDATION_WEIGHT = {
    "genre": 0.4,
    "artist": 0.3,
    "tempo": 0.2,
    "popularity": 0.1
}