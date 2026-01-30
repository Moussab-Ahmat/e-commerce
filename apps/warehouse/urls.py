"""
URLs for warehouse app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WarehouseOrderViewSet

router = DefaultRouter()
router.register(r'orders', WarehouseOrderViewSet, basename='warehouse-order')

urlpatterns = [
    path('', include(router.urls)),
]
