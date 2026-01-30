"""
URLs for risk app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlacklistViewSet, CodLimitRuleViewSet

router = DefaultRouter()
router.register(r'blacklist', BlacklistViewSet, basename='blacklist')
router.register(r'cod-limits', CodLimitRuleViewSet, basename='cod-limit')

urlpatterns = [
    path('', include(router.urls)),
]
