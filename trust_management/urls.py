from django.urls import path
from .views import TrustedDevicesView, SecurityEventsView, TrustIndicatorsView

urlpatterns = [
    path('devices/', TrustedDevicesView.as_view(), name='trusted_devices'),
    path('devices/<int:device_id>/', TrustedDevicesView.as_view(), name='remove_device'),
    path('events/', SecurityEventsView.as_view(), name='security_events'),
    path('indicators/', TrustIndicatorsView.as_view(), name='trust_indicators'),
]
