from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from .models import Order, OrderItem
from .serializers import OrderSerializer, AdminOrderSerializer
from cart.models import Cart
from products.models import Product
from users.permissions import HasAnyRole, IsAdminOrProductManager


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items').order_by('-created_at')


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class AdminOrderListView(generics.ListAPIView):
    """Admin: all orders with customer + payment info."""
    serializer_class = AdminOrderSerializer
    permission_classes = (IsAdminOrProductManager,)

    def get_queryset(self):
        qs = Order.objects.select_related('user').prefetch_related('items', 'payment').order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(id__iexact=search) |
                Q(user__email__icontains=search) |
                Q(user__name__icontains=search)
            )
        return qs


class AdminOrderStatusView(APIView):
    """Admin: update order status."""
    permission_classes = (IsAdminOrProductManager,)

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status')
        valid = [c[0] for c in Order.STATUS_CHOICES]
        if new_status not in valid:
            return Response({'error': f'status must be one of: {valid}'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = new_status
        order.save(update_fields=['status'])
        return Response(AdminOrderSerializer(order).data)


class AdminAnalyticsView(APIView):
    """Admin: aggregated analytics for dashboard."""
    permission_classes = (HasAnyRole,)
    allowed_roles = ('admin', 'manager', 'security', 'auditor')

    def get(self, request):
        from django.contrib.auth import get_user_model
        from trust_management.models import SecurityEvent, TrustedDevice
        from payments.models import Payment
        User = get_user_model()

        # Monthly sales (last 6 months)
        monthly = (
            Order.objects
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(sales=Sum('total_amount'), orders=Count('id'))
            .order_by('month')
        )[max(0, Order.objects.annotate(m=TruncMonth('created_at')).values('m').distinct().count() - 6):]

        monthly_sales = [
            {'month': r['month'].strftime('%b %Y'), 'sales': float(r['sales'] or 0), 'orders': r['orders']}
            for r in monthly
        ]

        # Orders by status
        status_counts = {
            r['status']: r['count']
            for r in Order.objects.values('status').annotate(count=Count('id'))
        }

        # Face verification stats
        total_orders = Order.objects.count()
        face_verified_orders = Order.objects.filter(face_verified=True).count()

        # Security summary
        total_events = SecurityEvent.objects.count()
        failed_logins = SecurityEvent.objects.filter(event_type__in=['login_failure', 'login_failed']).count()
        face_failures = SecurityEvent.objects.filter(event_type__in=['face_failed', 'face_verification_failed', 'face_verify_failure']).count()
        suspicious = SecurityEvent.objects.filter(event_type__in=['suspicious_login', 'multiple_face_failures']).count()

        return Response({
            'monthly_sales': monthly_sales,
            'orders_by_status': status_counts,
            'total_orders': total_orders,
            'face_verified_orders': face_verified_orders,
            'face_verification_rate': round(face_verified_orders / total_orders * 100, 1) if total_orders else 0,
            'total_users': User.objects.count(),
            'face_enrolled_users': User.objects.filter(is_face_enrolled=True).count(),
            'trusted_devices': TrustedDevice.objects.count(),
            'security_events': total_events,
            'failed_logins': failed_logins,
            'face_failures': face_failures,
            'suspicious_activities': suspicious,
            'total_revenue': float(Order.objects.aggregate(t=Sum('total_amount'))['t'] or 0),
            'successful_payments': Payment.objects.filter(status='success').count(),
            'failed_payments': Payment.objects.filter(status='failed').count(),
        })


class CheckoutView(APIView):
    @transaction.atomic
    def post(self, request):
        from django.utils import timezone
        from datetime import timedelta
        user = request.user
        if not user.face_verified_at or (timezone.now() - user.face_verified_at) > timedelta(minutes=5):
            return Response({'error': 'Facial verification required for checkout'}, status=status.HTTP_403_FORBIDDEN)

        try:
            cart = Cart.objects.prefetch_related('items__product').get(user=request.user)
        except Cart.DoesNotExist:
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

        # Lock product rows to prevent overselling
        item_list = list(cart.items.select_related('product').select_for_update())

        for item in item_list:
            if item.product.stock < item.quantity:
                return Response(
                    {'error': f'Insufficient stock for "{item.product.name}"'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        order = Order.objects.create(
            user=request.user,
            total_amount=cart.total,
            face_verified=True,
        )

        for item in item_list:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.product.price,
            )
            item.product.stock -= item.quantity
            item.product.save(update_fields=['stock'])

        cart.items.all().delete()
        user.face_verified_at = None
        user.save(update_fields=['face_verified_at'])
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
