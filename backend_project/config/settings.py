"""
Django settings for the Sejong backend.

Данные хранятся в Firebase Firestore через FireO (см. api/models.py).
SQLite используется только для внутренних нужд Django (сессии, админка).
"""

import os
from pathlib import Path

import fireo
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Переменные окружения из backend_project/.env
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-q7h@u9ag13!(qb=)#uip@voq!wks4j9p@#z2s_arz4$!q!w#=n",
)

DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

# --- Firebase / Firestore -------------------------------------------------

FIREBASE_CREDENTIALS = os.getenv(
    "FIREBASE_CREDENTIALS",
    str(BASE_DIR / "sejong-app-f1886-firebase-adminsdk-fbsvc-6981d46b30.json"),
)

# Подключение FireO к Firestore (один раз при старте проекта)
fireo.connection(from_file=FIREBASE_CREDENTIALS)

# --- Application definition -----------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "users",
    "ebook_and_chat",
    "info",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite — только для служебных таблиц Django, бизнес-данные лежат в Firestore
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- REST Framework --------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}

# --- Google Drive (аватары) -----------------------------------------------

GOOGLE_DRIVE_CREDENTIALS = os.getenv(
    'GOOGLE_DRIVE_CREDENTIALS',
    str(BASE_DIR / 'sejong-cloud-ff73493133e6.json'),
)
GOOGLE_DRIVE_AVATAR_FOLDER_ID = os.getenv('GOOGLE_DRIVE_AVATAR_FOLDER_ID', '')


# --- CORS (доступ для мобильного приложения и сайта) -----------------------

if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    # В продакшене перечислите домены сайта через запятую в .env:
    # CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com
    CORS_ALLOWED_ORIGINS = [
        o for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o
    ]
