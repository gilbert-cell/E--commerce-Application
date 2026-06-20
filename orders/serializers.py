from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'product_name', 'quantity', 'unit_price', 'subtotal')


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'status', 'total_amount', 'face_verified', 'items', 'created_at', 'updated_at')
        read_only_fields = ('id', 'total_amount', 'face_verified', 'created_at', 'updated_at')


class AdminOrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name  = serializers.CharField(source='user.name',  read_only=True)
    customer_email = serializers.CharField(source='user.email', read_only=True)
    payment_status = serializers.SerializerMethodField()
    payment_ref    = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'status', 'total_amount', 'face_verified', 'items',
                  'customer_name', 'customer_email', 'payment_status', 'payment_ref',
                  'created_at', 'updated_at')

    def get_payment_status(self, obj):
        return obj.payment.status if hasattr(obj, 'payment') else 'unpaid'

    def get_payment_ref(self, obj):
        return obj.payment.reference if hasattr(obj, 'payment') else None
