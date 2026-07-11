import re

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings
from facial_auth.utils import decode_image_from_base64, get_face_embedding, encrypt_embedding
from trust_management.utils import log_security_event

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=User.objects.all(), message='Email already exists'),
        ]
    )
    password = serializers.CharField(write_only=True, min_length=8)

    # Enrollment throttling settings (per-email or per-IP)
    MAX_ENROLL_ATTEMPTS = getattr(settings, 'MAX_FACE_ENROLL_ATTEMPTS', 3)
    ENROLL_WINDOW_SECONDS = getattr(settings, 'FACE_ENROLL_WINDOW_SECONDS', 60 * 60)

    class Meta:
        model = User
        fields = ('email', 'name', 'password', 'image')

    # Make image required for registration (mandatory enrollment)
    image = serializers.CharField(write_only=True, required=True, allow_blank=False)

    def validate(self, attrs):
        """Validate and preprocess the provided face image. Enforces rate-limits on failures."""
        image_b64 = attrs.get('image')
        request = self.context.get('request')
        email = attrs.get('email')

        # Build a simple throttle key using email or client IP
        ip = None
        if request is not None:
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
        throttle_key = f"face_enroll:{email or ip}"
        attempts = cache.get(throttle_key, 0)
        if attempts >= self.MAX_ENROLL_ATTEMPTS:
            raise serializers.ValidationError({'image': 'Too many failed face enrollment attempts. Try again later.'})

        # Decode and extract embedding
        image_obj = decode_image_from_base64(image_b64)
        if image_obj is None:
            cache.set(throttle_key, attempts + 1, self.ENROLL_WINDOW_SECONDS)
            remaining = max(self.MAX_ENROLL_ATTEMPTS - (attempts + 1), 0)
            raise serializers.ValidationError({'image': f'Invalid image data. Attempts remaining: {remaining}.'})

        embedding, error = get_face_embedding(image_obj)
        if embedding is None:
            cache.set(throttle_key, attempts + 1, self.ENROLL_WINDOW_SECONDS)
            remaining = max(self.MAX_ENROLL_ATTEMPTS - (attempts + 1), 0)
            raise serializers.ValidationError({'image': f'{error} Attempts remaining: {remaining}.'})

        # Successful: attach encrypted embedding to attrs and clear throttle
        try:
            attrs['face_embedding'] = encrypt_embedding(embedding.tolist())
            attrs['is_face_enrolled'] = True
            cache.delete(throttle_key)
        except Exception:
            # If encryption fails, treat as a temporary failure
            cache.set(throttle_key, attempts + 1, self.ENROLL_WINDOW_SECONDS)
            remaining = max(self.MAX_ENROLL_ATTEMPTS - (attempts + 1), 0)
            raise serializers.ValidationError({'image': f'Failed to process face image. Attempts remaining: {remaining}.'})

        return attrs

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError('Name is required')
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Name must be at least 2 characters')
        return value.strip()

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError('Password must include an uppercase letter')
        if not re.search(r'\d', value):
            raise serializers.ValidationError('Password must include a number')
        return value

    def create(self, validated_data):
        # `validate` has already attached `face_embedding` and `is_face_enrolled` on success.
        image_b64 = validated_data.pop('image', None)
        face_embedding = validated_data.pop('face_embedding', None)
        face_enrolled = validated_data.pop('is_face_enrolled', False)

        user = User.objects.create_user(**validated_data, face_embedding=face_embedding, is_face_enrolled=face_enrolled)

        request = self.context.get('request')
        try:
            if face_enrolled and request is not None:
                log_security_event(user, 'face_enrolled', request)
        except Exception:
            # Logging failure should not block the response
            pass

        return user


class UserSerializer(serializers.ModelSerializer):
    order_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'name', 'role', 'is_face_enrolled', 'is_verified',
            'is_staff', 'date_joined', 'last_login', 'order_count',
        )
        read_only_fields = (
            'id', 'role', 'is_face_enrolled', 'is_verified', 'is_staff',
            'date_joined', 'last_login', 'order_count',
        )
