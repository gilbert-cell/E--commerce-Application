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


def compute_trust_score(user) -> dict:
    """
    Calculate trust score (0-100) based on trust factors.
    Returns score, level, and breakdown.
    """
    from django.utils import timezone
    from datetime import timedelta
    from orders.models import Order
    from products.models import Review

    breakdown = {}

    # Face verified (+20)
    breakdown['face_verified'] = 20 if user.is_face_enrolled else 0

    # Email verified (+15)
    breakdown['email_verified'] = 15 if user.is_verified else 0

    # Trusted device registered (+15)
    has_trusted_device = user.trusted_devices.filter(is_trusted=True).exists()
    breakdown['trusted_device'] = 15 if has_trusted_device else 0

    # Successful transactions (+20, capped)
    successful_orders = Order.objects.filter(
        user=user, status__in=['confirmed', 'shipped', 'delivered']
    ).count()
    breakdown['successful_transactions'] = min(20, successful_orders * 5)

    # Positive reviews (+10, capped)
    review_count = Review.objects.filter(user=user).count()
    breakdown['positive_reviews'] = min(10, review_count * 3)

    # No suspicious activity in last 30 days (+20)
    since = timezone.now() - timedelta(days=30)
    suspicious = SecurityEvent.objects.filter(
        user=user,
        event_type__in=['face_failed', 'suspicious_login', 'multiple_face_failures'],
        created_at__gte=since,
    ).count()
    breakdown['no_suspicious_activity'] = max(0, 20 - suspicious * 5)

    score = min(100, max(0, sum(breakdown.values())))

    if score >= 80:
        level = 'HIGH'
    elif score >= 50:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {'score': score, 'level': level, 'breakdown': breakdown}


def detect_fraud_flags(user) -> list:
    """Return list of active fraud/risk flags for a user."""
    from django.utils import timezone
    from datetime import timedelta
    from orders.models import Order

    flags = []
    now = timezone.now()

    # Multiple face failures in last hour
    face_failures = SecurityEvent.objects.filter(
        user=user, event_type='face_failed',
        created_at__gte=now - timedelta(hours=1)
    ).count()
    if face_failures >= 3:
        flags.append({
            'type': 'multiple_face_failures',
            'detail': f'{face_failures} face failures in last hour',
            'severity': 'high',
        })

    # Suspicious login events this week
    suspicious = SecurityEvent.objects.filter(
        user=user, event_type='suspicious_login',
        created_at__gte=now - timedelta(days=7)
    ).count()
    if suspicious > 0:
        flags.append({
            'type': 'suspicious_login',
            'detail': f'{suspicious} suspicious login(s) this week',
            'severity': 'high',
        })

    # High-value orders without face verification
    high_value = Order.objects.filter(
        user=user, face_verified=False, total_amount__gte=500,
        created_at__gte=now - timedelta(days=30)
    ).count()
    if high_value > 0:
        flags.append({
            'type': 'unverified_high_value',
            'detail': f'{high_value} high-value order(s) without face verification',
            'severity': 'medium',
        })

    # No trusted device
    if not user.trusted_devices.filter(is_trusted=True).exists():
        flags.append({
            'type': 'no_trusted_device',
            'detail': 'No trusted device registered',
            'severity': 'low',
        })

    return flags


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

    # Auto-flag multiple face failures when risk is critical
    if event_type == 'face_failed' and risk >= 0.75:
        SecurityEvent.objects.get_or_create(
            user=user,
            event_type='multiple_face_failures',
            defaults={'ip_address': ip, 'user_agent': ua, 'risk_score': risk},
        )
