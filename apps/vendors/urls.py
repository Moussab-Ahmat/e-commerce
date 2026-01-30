"""
URL configuration for vendor API endpoints.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'dashboard', views.VendorDashboardViewSet, basename='vendor-dashboard')
router.register(r'products', views.VendorProductViewSet, basename='vendor-products')
router.register(r'orders', views.VendorOrderViewSet, basename='vendor-orders')

urlpatterns = [
    path('', include(router.urls)),
]
