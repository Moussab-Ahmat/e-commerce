"""
URLs for delivery app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeliveryZoneViewSet

router = DefaultRouter()
router.register(r'zones', DeliveryZoneViewSet, basename='delivery-zone')

urlpatterns = [
    path('', include(router.urls)),
]

