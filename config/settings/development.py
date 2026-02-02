"""
Development settings for OIUEEI project.
Uses SQLite and console email backend.
"""

from .base import *  # noqa: F401, F403

DEBUG = True

# Database: SQLite for development
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# Email: Console backend for development
# Magic link emails will be printed to the terminal
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS: Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
