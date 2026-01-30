"""
Settings module initialization.
Loads environment-specific settings based on ENVIRONMENT variable.
"""
import os
from decouple import config

ENVIRONMENT = config('ENVIRONMENT', default='development')

if ENVIRONMENT == 'production':
    from .production import *
else:
    from .development import *
