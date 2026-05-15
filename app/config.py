import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///sistema_educacional.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx'}

    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'ollama').strip().lower()
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434').rstrip('/')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'gemma3:12b')
    OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '180'))
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_URL = os.environ.get(
        'GEMINI_URL',
        'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent'
    )
