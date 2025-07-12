"""
Production settings for drawtwo project.
"""

import os  # noqa: F401

from .base import *  # noqa: F401,F403

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Production allowed hosts (should be set via environment variable)
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# CORS settings for production - configurable via environment
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")

# Frontend URL configuration for production
FRONTEND_URL = os.environ.get("FRONTEND_URL")
FRONTEND_EMAIL_CONFIRM_URL = os.environ.get("FRONTEND_EMAIL_CONFIRM_URL")

# JWT settings for production
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_COOKIE": None,  # Disable cookie-based JWT
    "JWT_AUTH_REFRESH_COOKIE": None,  # Disable cookie-based refresh
    "JWT_AUTH_SECURE": True,  # Enable secure cookies in production
    "JWT_AUTH_HTTPONLY": False,  # Not using cookies
    "JWT_AUTH_SAMESITE": None,  # Not using cookies
    "USER_DETAILS_SERIALIZER": "apps.authentication.serializers.UserSerializer",
    "PASSWORD_RESET_CONFIRM_URL": "auth/password/reset/confirm/{uid}/{token}/",
    "REGISTER_SERIALIZER": "apps.authentication.serializers.CustomRegisterSerializer",
    "TOKEN_MODEL": None,  # We're using JWT, not tokens
}

# Google OAuth settings for production
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_OAUTH2_CLIENT_ID"),
            "secret": os.environ.get("GOOGLE_OAUTH2_CLIENT_SECRET"),
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "OAUTH_PKCE_ENABLED": True,
    }
}

# Email settings for production - AWS SES
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "email-smtp.us-east-1.amazonaws.com")  # Default SES SMTP endpoint
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("AWS_SES_ACCESS_KEY_ID")  # AWS SES SMTP username
EMAIL_HOST_PASSWORD = os.environ.get("AWS_SES_SECRET_ACCESS_KEY")  # AWS SES SMTP password
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")
SERVER_EMAIL = os.environ.get("SERVER_EMAIL")  # For error emails

# AWS SES Configuration
AWS_SES_REGION_NAME = os.environ.get("AWS_SES_REGION_NAME", "us-east-1")
AWS_SES_REGION_ENDPOINT = f"email.{AWS_SES_REGION_NAME}.amazonaws.com"

# Logging configuration for production
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Static files for production
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
