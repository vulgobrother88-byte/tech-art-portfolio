import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    DATABASE_URL = f"sqlite:///{BASE_DIR / DATABASE_URL.removeprefix('sqlite:///')}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-development-key")
    PIX_ENCRYPTION_KEY = os.getenv("PIX_ENCRYPTION_KEY", "")
    ENVIRONMENT = os.getenv("FLASK_ENV", "development").lower()
    SQLALCHEMY_DATABASE_URI = DATABASE_URL or f"sqlite:///{BASE_DIR / 'instance' / 'techart.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    PRODUCT_MAX_CONTENT_LENGTH = 100 * 1024 * 1024
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    PRODUCT_FILES_FOLDER = Path(os.getenv("PRODUCT_FILES_FOLDER", str(BASE_DIR / "private_products")))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = ENVIRONMENT == "production"
    SESSION_COOKIE_NAME = "techart_session"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8
    SESSION_REFRESH_EACH_REQUEST = False
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOGIN_WINDOW_MINUTES = int(os.getenv("LOGIN_WINDOW_MINUTES", "15"))
    MAX_IMAGE_SIZE = 8 * 1024 * 1024
    WTF_CSRF_TIME_LIMIT = 60 * 60
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
