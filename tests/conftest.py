"""
Pytest configuration and fixtures.
"""
import pytest
from django.conf import settings
from django.test.utils import override_settings
from django.core.cache import cache


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests."""
    pass


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """API client fixture."""
    from rest_framework.test import APIClient
    return APIClient()

