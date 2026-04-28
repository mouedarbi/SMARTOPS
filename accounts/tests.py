from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class CustomUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password='password123',
            role='technician'
        )

    def test_create_user(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.role, 'technician')
        self.assertTrue(self.user.is_active)

    def test_role_properties(self):
        self.assertTrue(self.user.is_technician)
        self.assertFalse(self.user.is_admin)
        
        self.user.role = 'admin'
        self.user.save()
        self.assertTrue(self.user.is_admin)
        self.assertFalse(self.user.is_technician)

    def test_soft_delete(self):
        self.assertFalse(self.user.is_deleted)
        self.user.soft_delete()
        self.assertTrue(self.user.is_deleted)
        self.assertIsNotNone(self.user.deleted_at)
        self.assertLessEqual(self.user.deleted_at, timezone.now())

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), "testuser (Technicien)")
