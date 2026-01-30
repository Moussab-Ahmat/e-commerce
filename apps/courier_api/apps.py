"""Courier API app configuration."""
from django.apps import AppConfig


class CourierApiConfig(AppConfig):
    """Courier API app config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.courier_api'
    verbose_name = 'Courier API'
