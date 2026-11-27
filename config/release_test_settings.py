from pathlib import Path
from config.settings import *

_BASE = Path(r"C:\Users\Igor\AppData\Local\Temp\asics-release-test")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_BASE / "db.sqlite3"),
    }
}
MEDIA_ROOT = str(_BASE / "media")
STATIC_ROOT = str(_BASE / "staticfiles")
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
