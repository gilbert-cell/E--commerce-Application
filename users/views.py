from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Count
from .serializers import RegisterSerializer, UserSerializer
from .permissions import IsAdminRole

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'error': 'Both old_password and new_password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({'error': 'Invalid current password'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'Password must be at least 8 characters'}, status=status.HTTP_400_BAD_REQUEST)

        if old_password == new_password:
            return Response({'error': 'New password must differ from current password'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password updated successfully'})


class UserListView(generics.ListAPIView):
    """Admin: list all users."""
    queryset = User.objects.annotate(order_count=Count('orders')).order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = (IsAdminRole,)


class UserDetailView(generics.RetrieveAPIView):
    """Admin: get user details."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAdminRole,)


class AssignRoleView(APIView):
    """Admin: assign a role to a user."""
    permission_classes = (IsAdminRole,)

    def patch(self, request, pk):
        role = request.data.get('role')
        valid_roles = {choice[0] for choice in User.ROLE_CHOICES}
        if role not in valid_roles:
            return Response({'error': f'role must be one of: {", ".join(sorted(valid_roles))}'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user and role != User.ROLE_ADMIN:
            return Response({'error': 'You cannot remove your own admin role'}, status=status.HTTP_400_BAD_REQUEST)

        user.role = role
        user.is_staff = role == User.ROLE_ADMIN or user.is_superuser
        user.save(update_fields=['role', 'is_staff'])
        return Response(UserSerializer(user).data)


class UserDeactivateView(APIView):
    """Admin: deactivate/activate a user account."""
    permission_classes = (IsAdminRole,)

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user:
            return Response({'error': 'You cannot deactivate your own account'}, status=status.HTTP_400_BAD_REQUEST)

        is_active = request.data.get('is_active', not user.is_active)
        user.is_active = is_active
        user.save(update_fields=['is_active'])
        return Response({
            'message': f'User has been {"activated" if is_active else "deactivated"}',
            **UserSerializer(user).data
        })


class UserDeleteView(APIView):
    """Admin: permanently delete a user account."""
    permission_classes = (IsAdminRole,)

    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user:
            return Response({'error': 'You cannot delete your own account'}, status=status.HTTP_400_BAD_REQUEST)

        email = user.email
        user.delete()
        return Response({'message': f'User {email} has been permanently deleted'}, status=status.HTTP_204_NO_CONTENT)


class ResetUserPasswordView(APIView):
    """Admin: reset a user's password."""
    permission_classes = (IsAdminRole,)

    def post(self, request, pk):
        password = request.data.get('password')
        if not password or len(password) < 8:
            return Response(
                {'error': 'A new password of at least 8 characters is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if user == request.user:
            return Response({'error': 'You cannot reset your own password here.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'message': 'Password reset successfully.', 'user': UserSerializer(user).data})
