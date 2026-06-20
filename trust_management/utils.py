from .models import SecurityEvent


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def compute_risk_score(user, event_type: str) -> float:
    """Heuristic risk scoring based on failures in the last 24 hours."""
    from django.utils import timezone
    from datetime import timedelta
    if event_type == 'face_failed':
        since = timezone.now() - timedelta(hours=24)
        recent_failures = SecurityEvent.objects.filter(
            user=user, event_type='face_failed', created_at__gte=since
        ).count()
        return min(1.0, recent_failures * 0.25)
    return 0.0


def log_security_event(user, event_type: str, request=None):
    ip = get_client_ip(request) if request else None
    ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
    risk = compute_risk_score(user, event_type)

    SecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        ip_address=ip,
        user_agent=ua,
        risk_score=risk,
    )
