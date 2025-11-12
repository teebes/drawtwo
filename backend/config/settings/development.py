"""
Development settings for drawtwo project.
"""

from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS  # noqa: F401

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allow connections from local network for mobile testing
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "backend", ".local", "*"]

# Development-specific apps
INSTALLED_APPS += [
    "django_extensions",
]

# Development database settings (can override base if needed)
# DATABASES['default']['HOST'] = 'localhost'  # Uncomment if running DB locally

# Email backend for development (console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Logging configuration for development
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

# CORS settings for development
CORS_ALLOW_ALL_ORIGINS = True

# Redis host configuration for Docker
import os
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")

# Update CHANNEL_LAYERS for development
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(REDIS_HOST, 6379)],
            "prefix": "drawtwo:ws:",
        },
    },
}
