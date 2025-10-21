"""
Test settings for drawtwo project.
"""

import os
from .base import *  # noqa: F401,F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use in-memory channel layer for tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}

# Celery settings for tests - run tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email backend for tests (in-memory)
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Logging configuration for tests
# Set TEST_LOG_LEVEL=DEBUG to see verbose debug output during tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {name}: {message}',
            'style': '{',
        },
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': os.environ.get('TEST_LOG_LEVEL', 'WARNING'),
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('TEST_LOG_LEVEL', 'WARNING'),
    },
    'loggers': {
        'apps': {
            'handlers': ['console'],
            'level': os.environ.get('TEST_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Disable migrations for faster tests (optional - uncomment if needed)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# MIGRATION_MODULES = DisableMigrations()
