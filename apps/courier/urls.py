"""
URLs for courier app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CourierDeliveryViewSet

router = DefaultRouter()
router.register(r'deliveries', CourierDeliveryViewSet, basename='courier-delivery')

urlpatterns = [
    path('', include(router.urls)),
]
