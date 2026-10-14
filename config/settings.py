import mimetypes
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

mimetypes.add_type("image/webp", ".webp", strict=True)
mimetypes.add_type("font/otf", ".otf", strict=True)

BASE_DIR = Path(__file__).resolve().parent.parent

_DEV_SECRET = "dev-only-asics-shoe-finder-change-before-production"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _DEV_SECRET)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
if not DEBUG and SECRET_KEY == _DEV_SECRET:
    raise ImproperlyConfigured("Postavi DJANGO_SECRET_KEY za produkciju.")

_hosts = os.environ.get("DJANGO_ALLOWED_HOSTS", "*" if DEBUG else "")
ALLOWED_HOSTS = [host.strip() for host in _hosts.split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = os.environ.get("DJANGO_SECURE_SSL", "1") == "1"
    CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE

_script_name = os.environ.get("DJANGO_SCRIPT_NAME", "").strip()
if _script_name:
    FORCE_SCRIPT_NAME = _script_name

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "finder",
]

MIDDLEWARE = [
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
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

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
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "sr-latn"
TIME_ZONE = "Europe/Belgrade"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    ("assets", BASE_DIR / "assets"),
]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
