"""
URLs for deliveries app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeliveryAgentViewSet, DeliveryViewSet

router = DefaultRouter()
router.register(r'agents', DeliveryAgentViewSet, basename='delivery-agent')
router.register(r'deliveries', DeliveryViewSet, basename='delivery')

urlpatterns = [
    path('', include(router.urls)),
]

