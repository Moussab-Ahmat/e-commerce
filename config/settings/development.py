"""
Development settings.
"""
from .base import *

DEBUG = True

# Allow all hosts in development (important for physical device testing)
ALLOWED_HOSTS = ['*']

# Allow all CORS in development (override base.py)
CORS_ALLOW_ALL_ORIGINS = True
# Remove the restrictive CORS_ALLOWED_ORIGINS from base.py
CORS_ALLOWED_ORIGINS = []  # Empty list means use CORS_ALLOW_ALL_ORIGINS

# Additional CORS settings for Flutter Web compatibility
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'idempotency-key',  # Custom header for order creation
]
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Logging - more verbose in development
LOGGING['handlers']['console']['formatter'] = 'verbose'
LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'
