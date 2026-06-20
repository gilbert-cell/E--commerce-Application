import numpy as np
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase, override_settings
from unittest.mock import patch

from .serializers import FaceImageSerializer
from .utils import compare_faces, decode_image_from_base64, decrypt_embedding, encrypt_embedding


class FacialAuthUtilsTests(TestCase):
    def test_encrypt_decrypt_embedding_roundtrip(self):
        embedding = np.random.rand(128).astype(np.float64).tolist()
        encrypted = encrypt_embedding(embedding)
        decrypted = decrypt_embedding(encrypted)

        self.assertEqual(decrypted.dtype, np.float64)
        self.assertEqual(decrypted.shape, (128,))
        self.assertTrue(np.allclose(decrypted, np.array(embedding, dtype=np.float64)))

    def test_compare_faces_returns_true_for_same_embedding(self):
        embedding = np.random.rand(128).astype(np.float64)
        encrypted = encrypt_embedding(embedding.tolist())

        self.assertTrue(compare_faces(encrypted, embedding, tolerance=0.01))

    def test_compare_faces_returns_false_for_different_embedding(self):
        embedding = np.random.rand(128).astype(np.float64)
        encrypted = encrypt_embedding(embedding.tolist())
        different_embedding = embedding + 0.5

        self.assertFalse(compare_faces(encrypted, different_embedding, tolerance=0.01))

    def test_decode_image_from_base64_invalid_returns_none(self):
        self.assertIsNone(decode_image_from_base64('not-base64'))


class FaceImageSerializerTests(TestCase):
    def test_serializer_rejects_missing_image(self):
        serializer = FaceImageSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('image', serializer.errors)

    def test_serializer_rejects_blank_image(self):
        serializer = FaceImageSerializer(data={'image': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('image', serializer.errors)


class FaceAuthViewsTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='shopper@example.com',
            name='Shopper',
            password='secure-password-123',
        )
        self.client.force_authenticate(user=self.user)

    def test_enroll_requires_image(self):
        response = self.client.post('/api/facial-auth/enroll/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)

    def test_verify_requires_image(self):
        response = self.client.post('/api/facial-auth/verify/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('image', response.data)

    @patch('facial_auth.views.get_face_embedding')
    @patch('facial_auth.views.decode_image_from_base64')
    def test_enroll_saves_face_embedding(self, mock_decode_image, mock_get_face_embedding):
        mock_decode_image.return_value = np.zeros((10, 10, 3), dtype=np.uint8)
        mock_get_face_embedding.return_value = (np.ones(128, dtype=np.float64), None)

        response = self.client.post('/api/facial-auth/enroll/', {'image': 'data:image/jpeg;base64,fake'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Face enrolled successfully')
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_face_enrolled)
        self.assertIsNotNone(self.user.face_embedding)

    @patch('facial_auth.views.get_face_embedding')
    @patch('facial_auth.views.decode_image_from_base64')
    @override_settings(DEBUG=True)
    def test_verify_auto_enrolls_unenrolled_face_in_debug(self, mock_decode_image, mock_get_face_embedding):
        mock_decode_image.return_value = np.zeros((10, 10, 3), dtype=np.uint8)
        mock_get_face_embedding.return_value = (np.zeros(128, dtype=np.float64), None)

        response = self.client.post('/api/facial-auth/verify/', {'image': 'data:image/jpeg;base64,fake'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['verified'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_face_enrolled)
        self.assertIsNotNone(self.user.face_embedding)
        self.assertIsNotNone(self.user.face_verified_at)
