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

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = False  # В продакшене всегда False! В .env можно переопределить на True для локальной разработки

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

SECURE_SSL_REDIRECT = True  # В продакшене True, в .env можно переопределить на False для локальной разработки

SECURE_PROXY_SSL_HEADER = (
    'HTTP_X_FORWARDED_PROTO',
    'https'
)

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
    "drf_spectacular",
    "corsheaders",
    "users",
    "groups",
    "ebook_and_chat",
    "info",
    "announcements",
    "audit_logs",
    "chat_group",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# --- drf-spectacular (OpenAPI / Swagger docs) ------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "Sejong Backend API",
    "DESCRIPTION": (
        "REST API мобильного приложения Sejong (пользователи, группы, "
        "электронные книги, расписание, уведомления, объявления, аудит-логи). "
        "Данные хранятся в Firebase Firestore, авторизация — через собственные JWT "
        "(заголовок `Authorization: Bearer <token>`)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "ENUM_NAME_OVERRIDES": {
        "StatusEnum": "users.serializers.STATUS_CHOICES",
    },
}

# --- Email (Gmail SMTP — коды сброса пароля) --------------------------------
# EMAIL_HOST_PASSWORD — это App Password (16 символов), не обычный пароль:
# myaccount.google.com → Security → 2-Step Verification → App passwords

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_TIMEOUT = 10  # секунд, чтобы запрос не висел при недоступности SMTP

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
