from django.urls import path
from .views import OrderListView, OrderDetailView, CheckoutView, AdminOrderListView, AdminOrderStatusView, AdminAnalyticsView

urlpatterns = [
    path('', OrderListView.as_view(), name='orders'),
    path('<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('admin/', AdminOrderListView.as_view(), name='admin_orders'),
    path('admin/<int:pk>/status/', AdminOrderStatusView.as_view(), name='admin_order_status'),
    path('admin/analytics/', AdminAnalyticsView.as_view(), name='admin_analytics'),
]
