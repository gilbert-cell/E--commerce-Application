from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase


class LoginTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='shopper@example.com',
            name='Shopper',
            password='secure-password-123',
        )

    def test_login_returns_tokens_for_valid_email_credentials(self):
        response = self.client.post(
            '/api/users/login/',
            {'email': self.user.email, 'password': 'secure-password-123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_rejects_invalid_credentials_without_server_error(self):
        response = self.client.post(
            '/api/users/login/',
            {'email': self.user.email, 'password': 'wrong-password'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RegisterTests(APITestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.register_url = '/api/users/register/'
        self.existing_user = self.user_model.objects.create_user(
            email='existing@example.com',
            name='Existing User',
            password='SecurePass123',
        )

    def test_register_requires_valid_name_email_and_password(self):
        response = self.client.post(self.register_url, {
            'name': '',
            'email': 'not-an-email',
            'password': 'weak',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(self.register_url, {
            'name': 'New User',
            'email': self.existing_user.email,
            'password': 'StrongPass1',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['email'][0], 'Email already exists')

    def test_register_rejects_password_without_uppercase_or_number(self):
        response = self.client.post(self.register_url, {
            'name': 'New User',
            'email': 'newuser@example.com',
            'password': 'lowercase1',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

        response2 = self.client.post(self.register_url, {
            'name': 'New User',
            'email': 'newuser2@example.com',
            'password': 'UpperCaseOnly',
        }, format='json')

        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response2.data)

    def test_register_returns_201_for_valid_request(self):
        response = self.client.post(self.register_url, {
            'name': 'Valid User',
            'email': 'valid@example.com',
            'password': 'ValidPass1',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(self.user_model.objects.filter(email='valid@example.com').exists())


class AdminUserManagementTests(APITestCase):
    """Tests for admin user management endpoints (role assignment, deactivation, deletion)."""

    def setUp(self):
        self.user_model = get_user_model()
        # Create admin user
        self.admin = self.user_model.objects.create_user(
            email='admin@example.com',
            name='Admin User',
            password='AdminPass1',
            role='admin',
        )
        # Create test users
        self.customer = self.user_model.objects.create_user(
            email='customer@example.com',
            name='Customer User',
            password='CustPass1',
            role='customer',
        )
        self.manager = self.user_model.objects.create_user(
            email='manager@example.com',
            name='Manager User',
            password='MgrPass1',
            role='manager',
        )

    def test_admin_can_list_all_users(self):
        """Admin should be able to list all users."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/users/admin/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # admin, customer, manager

    def test_non_admin_cannot_list_users(self):
        """Non-admin users should not be able to list users."""
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/users/admin/users/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_get_user_detail(self):
        """Admin should be able to retrieve user details."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'/api/users/admin/users/{self.customer.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.customer.email)
        self.assertEqual(response.data['role'], 'customer')

    def test_admin_can_assign_role_to_user(self):
        """Admin should be able to assign a role to a user."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/users/admin/users/{self.customer.id}/role/',
            {'role': 'security'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['role'], 'security')
        # Verify in database
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, 'security')

    def test_admin_cannot_remove_own_admin_role(self):
        """Admin should not be able to remove their own admin role."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/users/admin/users/{self.admin.id}/role/',
            {'role': 'customer'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        # Verify role unchanged
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, 'admin')

    def test_admin_rejects_invalid_role(self):
        """Admin should get error when assigning invalid role."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f'/api/users/admin/users/{self.customer.id}/role/',
            {'role': 'invalid_role'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_admin_can_deactivate_user(self):
        """Admin should be able to deactivate a user account."""
        self.client.force_authenticate(user=self.admin)
        self.assertTrue(self.customer.is_active)

        response = self.client.post(
            f'/api/users/admin/users/{self.customer.id}/deactivate/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])
        # Verify in database
        self.customer.refresh_from_db()
        self.assertFalse(self.customer.is_active)

    def test_admin_can_reactivate_user(self):
        """Admin should be able to reactivate a deactivated user account."""
        # First deactivate
        self.customer.is_active = False
        self.customer.save()

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f'/api/users/admin/users/{self.customer.id}/deactivate/',
            {'is_active': True},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_active'])
        # Verify in database
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.is_active)

    def test_admin_cannot_deactivate_own_account(self):
        """Admin should not be able to deactivate their own account."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            f'/api/users/admin/users/{self.admin.id}/deactivate/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        # Verify still active
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_can_delete_user(self):
        """Admin should be able to permanently delete a user account."""
        user_id = self.customer.id
        user_email = self.customer.email

        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/users/admin/users/{user_id}/delete/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify deleted from database
        self.assertFalse(self.user_model.objects.filter(id=user_id).exists())

    def test_admin_cannot_delete_own_account(self):
        """Admin should not be able to delete their own account."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.delete(f'/api/users/admin/users/{self.admin.id}/delete/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        # Verify still exists
        self.assertTrue(self.user_model.objects.filter(id=self.admin.id).exists())

    def test_admin_gets_404_for_nonexistent_user(self):
        """Admin should get 404 when trying to manage nonexistent user."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/users/admin/users/99999/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_non_admin_cannot_deactivate_user(self):
        """Non-admin users should not be able to deactivate users."""
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/api/users/admin/users/{self.manager.id}/deactivate/',
            {'is_active': False},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_admin_cannot_delete_user(self):
        """Non-admin users should not be able to delete users."""
        self.client.force_authenticate(user=self.customer)
        response = self.client.delete(f'/api/users/admin/users/{self.manager.id}/delete/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
