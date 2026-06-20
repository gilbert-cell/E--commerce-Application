from rest_framework import serializers


class FaceImageSerializer(serializers.Serializer):
    image = serializers.CharField(required=True, allow_blank=False)
