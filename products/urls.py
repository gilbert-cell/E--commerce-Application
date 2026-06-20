from django.urls import path
from .views import ProductListView, ProductDetailView, AdminProductView, AdminProductDetailView, CategoryListView, ReviewListCreateView

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('<int:pk>/reviews/', ReviewListCreateView.as_view(), name='product_reviews'),
    path('admin/', AdminProductView.as_view(), name='admin_products'),
    path('admin/<int:pk>/', AdminProductDetailView.as_view(), name='admin_product_detail'),
    path('categories/', CategoryListView.as_view(), name='categories'),
]
