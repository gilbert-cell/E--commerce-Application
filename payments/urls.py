from django.urls import path
from .views import InitiatePaymentView, PaymentStatusView, AdminPaymentListView, AdminPaymentRefundView

urlpatterns = [
    path('<int:order_id>/pay/', InitiatePaymentView.as_view(), name='pay'),
    path('<int:order_id>/status/', PaymentStatusView.as_view(), name='payment_status'),
    path('admin/', AdminPaymentListView.as_view(), name='admin_payments'),
    path('admin/<int:pk>/refund/', AdminPaymentRefundView.as_view(), name='admin_payment_refund'),
]
