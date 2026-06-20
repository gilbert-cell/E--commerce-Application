import logging

import numpy as np
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import FaceImageSerializer
from .utils import decode_image_from_base64, get_face_embedding, encrypt_embedding, compare_faces
from trust_management.utils import log_security_event

logger = logging.getLogger(__name__)


class EnrollFaceView(APIView):
    def post(self, request):
        serializer = FaceImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image_b64 = serializer.validated_data['image']
        logger.debug("Enroll image received: %s", bool(image_b64))
        image = decode_image_from_base64(image_b64)
        logger.debug("Enroll decoded image shape: %s", None if image is None else image.shape)
        if image is None:
            return Response({'error': 'Invalid image data'}, status=status.HTTP_400_BAD_REQUEST)

        embedding, error = get_face_embedding(image)
        if embedding is None:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.face_embedding = encrypt_embedding(embedding.tolist())
        user.is_face_enrolled = True
        user.save(update_fields=['face_embedding', 'is_face_enrolled'])

        log_security_event(user, 'face_enrolled', request)
        return Response({'message': 'Face enrolled successfully'})


LOCKOUT_MAX_FAILURES = 5
LOCKOUT_WINDOW_MINUTES = 30


class VerifyFaceView(APIView):
    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta
        from trust_management.models import SecurityEvent

        serializer = FaceImageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.is_face_enrolled or not user.face_embedding:
            if settings.DEBUG:
                logger.warning("DEBUG face auth bypass: auto-enrolling user before verification")
                user.face_embedding = encrypt_embedding(np.zeros(128, dtype=np.float64).tolist())
                user.is_face_enrolled = True
                user.save(update_fields=['face_embedding', 'is_face_enrolled'])
            else:
                return Response({'error': 'Face not enrolled'}, status=status.HTTP_400_BAD_REQUEST)

        # Account lockout check
        since = timezone.now() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
        recent_failures = SecurityEvent.objects.filter(
            user=user, event_type='face_failed', created_at__gte=since
        ).count()
        if recent_failures >= LOCKOUT_MAX_FAILURES:
            return Response(
                {'error': f'Account temporarily locked after {LOCKOUT_MAX_FAILURES} failed attempts. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        image_b64 = serializer.validated_data['image']
        logger.debug("Verify image received: %s", bool(image_b64))
        image = decode_image_from_base64(image_b64)
        logger.debug("Verify decoded image shape: %s", None if image is None else image.shape)
        if image is None:
            return Response({'error': 'Invalid image data'}, status=status.HTTP_400_BAD_REQUEST)

        embedding, error = get_face_embedding(image)
        if embedding is None:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        matched = compare_faces(bytes(user.face_embedding), embedding)
        log_security_event(user, 'face_verified' if matched else 'face_failed', request)

        if not matched:
            new_failures = recent_failures + 1
            if new_failures >= LOCKOUT_MAX_FAILURES:
                log_security_event(user, 'multiple_face_failures', request)
            remaining = LOCKOUT_MAX_FAILURES - new_failures
            return Response(
                {'verified': False, 'error': 'Face verification failed', 'attempts_remaining': max(remaining, 0)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user.face_verified_at = timezone.now()
        user.save(update_fields=['face_verified_at'])
        return Response({'verified': True})
