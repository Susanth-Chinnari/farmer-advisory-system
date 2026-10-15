"""
config.py - Application Configuration Module

Beginner-Friendly Explanation:
This module reads configuration settings from the operating system and the .env file.
It prevents hardcoding sensitive secrets (like API keys and passwords) directly in source code.
All other modules import configuration values from here.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory: Points to the project root (c:\CollegeProjects\StudentPortfolio)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if it exists
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

# Security: Secret key for Flask sessions and CSRF protection
# If not set in .env, falls back to a development default with a clear warning.
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-insecure-secret-key-change-in-production')

# Database Configuration: SQLite database file location
DATA_DIR = BASE_DIR / 'backend' / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = str(DATA_DIR / 'farmer_advisor.db')

# Uploads Configuration: Safe storage for uploaded crop images
UPLOAD_FOLDER = BASE_DIR / 'uploads'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# 5 MB maximum file upload size
MAX_UPLOAD_SIZE_MB = int(os.getenv('MAX_UPLOAD_SIZE_MB', 5))
MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Allowed image extensions for agricultural question attachments
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# AI Provider Settings: 'gemini', 'openai', or 'mock'
AI_PROVIDER = os.getenv('AI_PROVIDER', 'gemini').lower()
AI_MODEL_NAME = os.getenv('AI_MODEL_NAME', 'gemini-3-flash-preview')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()

# Weather Service Configuration
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '').strip()
DEFAULT_CITY = os.getenv('DEFAULT_CITY', 'Delhi,IN').strip()


def allowed_file(filename: str) -> bool:
    """
    Validates whether an uploaded file has a safe and permitted image extension.
    Example: 'leaf_rot.jpg' -> True, 'script.exe' -> False
    """
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS
