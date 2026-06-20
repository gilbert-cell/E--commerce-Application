from django.db import models
from django.conf import settings


class TrustedDevice(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trusted_devices')
    device_id = models.CharField(max_length=255)
    device_name = models.CharField(max_length=100, blank=True)
    last_login = models.DateTimeField(auto_now=True)
    is_trusted = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'device_id')


class SecurityEvent(models.Model):
    EVENT_TYPES = [
        ('face_enrolled', 'Face Enrolled'),
        ('face_verified', 'Face Verified'),
        ('face_failed', 'Face Verification Failed'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('suspicious_login', 'Suspicious Login'),
        ('multiple_face_failures', 'Multiple Face Failures'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='security_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    risk_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
