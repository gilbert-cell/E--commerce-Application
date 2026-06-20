import re

from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(queryset=User.objects.all(), message='Email already exists'),
        ]
    )
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'name', 'password')

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
        return User.objects.create_user(**validated_data)


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
