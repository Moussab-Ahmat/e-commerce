"""Courier API URL configuration."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourierDeliveryViewSet

router = DefaultRouter()
router.register(r'deliveries', CourierDeliveryViewSet, basename='courier-deliveries')

urlpatterns = [
    path('', include(router.urls)),
]
