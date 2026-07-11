from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from .models import TrustedDevice, SecurityEvent
from .utils import compute_trust_score, detect_fraud_flags
from users.permissions import CanViewSecurityEvents


class TrustedDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrustedDevice
        fields = ('id', 'device_id', 'device_name', 'last_login', 'is_trusted')


class SecurityEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = SecurityEvent
        fields = ('id', 'user_email', 'event_type', 'ip_address', 'risk_score', 'created_at')


class TrustedDevicesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        devices = TrustedDevice.objects.select_related('user')
        if getattr(request.user, 'role', None) not in {'admin', 'security'}:
            devices = devices.filter(user=request.user)
        return Response(TrustedDeviceSerializer(devices, many=True).data)

    def post(self, request):
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'device_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        device_name = request.data.get('device_name', '')
        device, _ = TrustedDevice.objects.update_or_create(
            user=request.user, device_id=device_id,
            defaults={'device_name': device_name, 'is_trusted': True}
        )
        return Response(TrustedDeviceSerializer(device).data)

    def delete(self, request, device_id):
        TrustedDevice.objects.filter(user=request.user, id=device_id).delete()
        return Response({'message': 'Device removed'})


class SecurityEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        events = SecurityEvent.objects.select_related('user').order_by('-created_at')
        if getattr(request.user, 'role', None) not in {'admin', 'security'}:
            events = events.filter(user=request.user)
        events = events[:100 if CanViewSecurityEvents().has_permission(request, self) else 20]
        return Response(SecurityEventSerializer(events, many=True).data)


class TrustIndicatorsView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({
            'https_enabled': True if settings.DEBUG else request.is_secure(),
            'face_auth_available': True,
            'payment_secured': True,
            'data_encrypted': True,
            'jwt_protected': True,
            'trusted_devices_enabled': True,
        })


class TrustScoreView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        result = compute_trust_score(request.user)
        return Response(result)


class FraudFlagsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        flags = detect_fraud_flags(request.user)
        return Response({'flags': flags, 'count': len(flags)})
