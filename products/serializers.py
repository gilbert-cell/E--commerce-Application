from rest_framework import serializers
from .models import Product, Category, Review


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class CategoryReferenceField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        if data in ('', None):
            return None

        if isinstance(data, str) and not data.isdigit():
            name = data.strip()
            if not name:
                return None

            category = Category.objects.filter(name__iexact=name).first()
            if category:
                return category

            category, _ = Category.objects.get_or_create(name=name.title())
            return category

        return super().to_internal_value(data)


class ProductSerializer(serializers.ModelSerializer):
    category = CategoryReferenceField(queryset=Category.objects.all(), required=False, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'description', 'price', 'stock', 'image', 'category', 'category_name', 'is_active', 'created_at')


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'user_name', 'rating', 'comment', 'is_face_verified', 'created_at')
        read_only_fields = ('user_name', 'is_face_verified', 'created_at')
