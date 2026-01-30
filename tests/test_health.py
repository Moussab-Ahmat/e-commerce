"""
Health check endpoint tests.
"""
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint(client):
    """Test that health endpoint returns 200 OK."""
    url = reverse('health')
    response = client.get(url)
    
    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    
    data = response.json()
    assert data['status'] == 'ok'
    assert data['service'] == 'django'

