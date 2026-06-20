from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenBlacklistView
from .views import (
    RegisterView, ProfileView, ChangePasswordView, UserListView, AssignRoleView,
    UserDetailView, UserDeactivateView, UserDeleteView, ResetUserPasswordView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('admin/users/', UserListView.as_view(), name='admin_user_list'),
    path('admin/users/<int:pk>/', UserDetailView.as_view(), name='admin_user_detail'),
    path('admin/users/<int:pk>/role/', AssignRoleView.as_view(), name='admin_assign_role'),
    path('admin/users/<int:pk>/deactivate/', UserDeactivateView.as_view(), name='admin_deactivate_user'),
    path('admin/users/<int:pk>/delete/', UserDeleteView.as_view(), name='admin_delete_user'),
    path('admin/users/<int:pk>/reset-password/', ResetUserPasswordView.as_view(), name='admin_user_reset_password'),
    path('', UserListView.as_view(), name='user_list'),
    path('<int:pk>/role/', AssignRoleView.as_view(), name='assign_role'),
]
