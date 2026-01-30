"""
Admin API URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminCategoryViewSet,
    AdminCourierViewSet,
    AdminOrderViewSet,
    AdminProductViewSet,
    AdminVendorViewSet,
    AdminAnalyticsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'categories', AdminCategoryViewSet, basename='admin-category')
router.register(r'couriers', AdminCourierViewSet, basename='admin-courier')
router.register(r'orders', AdminOrderViewSet, basename='admin-order')
router.register(r'products', AdminProductViewSet, basename='admin-product')
router.register(r'vendors', AdminVendorViewSet, basename='admin-vendor')
router.register(r'analytics', AdminAnalyticsViewSet, basename='admin-analytics')

urlpatterns = [
    path('', include(router.urls)),
]
