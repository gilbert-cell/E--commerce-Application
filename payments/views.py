import re
import uuid
from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from orders.models import Order
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    card_last4  = serializers.SerializerMethodField()
    cardholder  = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ('id', 'reference', 'amount', 'status', 'payment_method', 'card_last4', 'cardholder', 'created_at')

    def get_card_last4(self, obj):
        return obj.gateway_response.get('card_last4')

    def get_cardholder(self, obj):
        return obj.gateway_response.get('cardholder')


def _parse_expiry(expiry: str):
    """Parse MM/YY or MM/YYYY. Returns (month, year) ints or raises ValueError."""
    parts = expiry.strip().split('/')
    if len(parts) != 2:
        raise ValueError('Expiry must be MM/YY')
    mm, yy = parts
    if not mm.isdigit() or not yy.isdigit():
        raise ValueError('Expiry must contain only digits')
    month = int(mm)
    year  = int(yy)
    if month < 1 or month > 12:
        raise ValueError('Expiry month must be 01–12')
    # Accept both 2-digit and 4-digit year
    if year < 100:
        year += 2000
    return month, year


def validate_card(card_data: dict) -> dict:
    """
    Validate all card fields.
    Returns {'field': 'error message'} dict — empty means valid.
    """
    errors = {}
    number = card_data.get('number', '').replace(' ', '')
    name   = card_data.get('name', '').strip()
    expiry = card_data.get('expiry', '').strip()
    cvv    = card_data.get('cvv', '').strip()

    # --- Cardholder name ---
    if not name:
        errors['name'] = 'Cardholder name is required.'
    elif len(name) < 2:
        errors['name'] = 'Name is too short.'
    elif not re.match(r"^[A-Za-z\s\-'\.]+$", name):
        errors['name'] = 'Name may only contain letters, spaces, hyphens and apostrophes.'

    # --- Card number ---
    if not number:
        errors['number'] = 'Card number is required.'
    elif not number.isdigit():
        errors['number'] = 'Card number must contain only digits.'
    elif len(number) not in range(13, 20):
        errors['number'] = 'Card number must be 13–19 digits.'

    # --- Expiry ---
    if not expiry:
        errors['expiry'] = 'Expiry date is required.'
    else:
        try:
            month, year = _parse_expiry(expiry)
            today = date.today()
            # Card expires at end of the expiry month
            if (year, month) < (today.year, today.month):
                errors['expiry'] = 'Card has expired.'
        except ValueError as exc:
            errors['expiry'] = str(exc)

    # --- CVV ---
    if not cvv:
        errors['cvv'] = 'CVV is required.'
    elif not cvv.isdigit():
        errors['cvv'] = 'CVV must contain only digits.'
    elif len(cvv) not in (3, 4):
        errors['cvv'] = 'CVV must be 3 or 4 digits.'

    return errors


def mock_process_payment(amount: float, card_data: dict) -> dict:
    """Run validation then simulate gateway approval/decline."""
    errors = validate_card(card_data)
    if errors:
        return {'success': False, 'errors': errors}

    number = card_data['number'].replace(' ', '')

    return {
        'success':    True,
        'reference':  f'TXN-{uuid.uuid4().hex[:12].upper()}',
        'message':    'Payment processed successfully',
        'amount':     amount,
        'card_last4': number[-4:],
        'cardholder': card_data['name'].strip().upper(),
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class AdminPaymentListView(APIView):
    """Admin: list all payments."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('admin', 'manager', 'security'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        payments = Payment.objects.select_related('order__user').order_by('-created_at')
        data = []
        for p in payments:
            data.append({
                'id': p.id,
                'reference': p.reference,
                'amount': str(p.amount),
                'status': p.status,
                'payment_method': p.payment_method,
                'card_last4': p.gateway_response.get('card_last4'),
                'customer_name': p.order.user.name,
                'customer_email': p.order.user.email,
                'order_id': p.order.id,
                'created_at': p.created_at,
            })
        return Response(data)


class AdminPaymentRefundView(APIView):
    """Admin: mark a payment as refunded."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ('admin', 'manager'):
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        try:
            payment = Payment.objects.get(pk=pk)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
        if payment.status != 'success':
            return Response({'error': 'Only successful payments can be refunded'}, status=status.HTTP_400_BAD_REQUEST)
        payment.status = 'refunded'
        payment.save(update_fields=['status'])
        payment.order.status = 'cancelled'
        payment.order.save(update_fields=['status'])
        return Response({'message': 'Payment refunded', 'reference': payment.reference})


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        # Enforce credit card as the only accepted payment method
        method = request.data.get('payment_method', 'credit_card')
        if method != Payment.METHOD_CREDIT_CARD:
            return Response(
                {'error': 'Only credit card payments are accepted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(order, 'payment') and order.payment.status == 'success':
            return Response({'error': 'Order already paid'}, status=status.HTTP_400_BAD_REQUEST)

        card_data = request.data.get('card', {})
        result    = mock_process_payment(float(order.total_amount), card_data)

        if not result['success']:
            # Return per-field errors so the frontend can highlight each field
            return Response(
                {'errors': result.get('errors', {}), 'error': 'Payment failed. Please check your card details.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        payment, _ = Payment.objects.update_or_create(
            order=order,
            defaults={
                'payment_method': Payment.METHOD_CREDIT_CARD,
                'reference':      result['reference'],
                'amount':         order.total_amount,
                'status':         'success',
                'gateway_response': result,
            },
        )
        order.status = 'confirmed'
        order.save(update_fields=['status'])
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            payment = Payment.objects.get(order__id=order_id, order__user=request.user)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PaymentSerializer(payment).data)
