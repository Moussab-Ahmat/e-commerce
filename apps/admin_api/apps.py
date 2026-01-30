"""
Admin API app configuration.
"""
from django.apps import AppConfig


class AdminApiConfig(AppConfig):
    """Configuration for Admin API app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.admin_api'
    verbose_name = 'Admin API'
