"""
Main URL configuration.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/v1/catalog/', include('apps.catalog.urls')),
    path('api/v1/vendors/', include('apps.vendors.urls')),
    path('api/v1/delivery/', include('apps.delivery.urls')),
    path('api/v1/deliveries/', include('apps.deliveries.urls')),
    path('api/v1/inventory/', include('apps.inventory.urls')),
    path('api/v1/procurement/', include('apps.procurement.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/risk/', include('apps.risk.urls')),
    path('api/v1/warehouse/', include('apps.warehouse.urls')),
    path('api/v1/courier/', include('apps.courier.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/admin/', include('apps.admin_api.urls')),
    path('api/v1/admin/', include('apps.reports.urls')),
    path('api/v1/courier-dashboard/', include('apps.courier_api.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
