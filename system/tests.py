from django.test import TestCase
from system.forms import SystemConfigurationForm

class SystemConfigurationFormTests(TestCase):
    def test_website_without_protocol(self):
        """
        Tests that a website entered without http/https protocol is automatically
        prepended with http:// and passes validation.
        """
        form_data = {
            'company_name': 'Test Company',
            'company_address': 'Brussels, Belgium',
            'company_phone': '012345678',
            'company_email': 'test@company.be',
            'company_website': 'www.example.be',
            'company_vat': 'BE 0123.456.789',
        }
        form = SystemConfigurationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data['company_website'], 'http://www.example.be')

    def test_website_with_protocol(self):
        """
        Tests that a website entered with https protocol is preserved and passes validation.
        """
        form_data = {
            'company_name': 'Test Company',
            'company_address': 'Brussels, Belgium',
            'company_phone': '012345678',
            'company_email': 'test@company.be',
            'company_website': 'https://my-site.be',
            'company_vat': 'BE 0123.456.789',
        }
        form = SystemConfigurationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data['company_website'], 'https://my-site.be')

    def test_invalid_website(self):
        """
        Tests that an invalid website throws a validation error with a custom message.
        """
        form_data = {
            'company_name': 'Test Company',
            'company_address': 'Brussels, Belgium',
            'company_phone': '012345678',
            'company_email': 'test@company.be',
            'company_website': 'invalid_domain_name_with_spaces',
            'company_vat': 'BE 0123.456.789',
        }
        form = SystemConfigurationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("company_website", form.errors)
        self.assertEqual(
            form.errors['company_website'][0],
            "Format attendu : 'www.exemple.com' ou 'https://exemple.com' (les tirets du bas '_' sont autorisés)"
        )

    def test_website_with_underscore(self):
        """
        Tests that a domain name with an underscore passes validation.
        """
        form_data = {
            'company_name': 'Test Company',
            'company_address': 'Brussels, Belgium',
            'company_phone': '012345678',
            'company_email': 'test@company.be',
            'company_website': 'https://www.btp_ops.be',
            'company_vat': 'BE 0123.456.789',
        }
        form = SystemConfigurationForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors.as_text())
        self.assertEqual(form.cleaned_data['company_website'], 'https://www.btp_ops.be')



from django.test import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model


@override_settings(SECURE_SSL_REDIRECT=False, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class DashboardSyncBannerTests(TestCase):
    """La bannière « Mises à jour disponibles » a besoin de son conteneur (issue #6)."""

    def test_dashboard_has_sync_notification_container_and_guarded_script(self):
        from system.models import SystemConfiguration
        config = SystemConfiguration.get_instance()
        config.company_name = 'Ma Société'
        config.save()
        get_user_model().objects.create_user(username='manager1', password='password123', role='manager')
        self.client.login(username='manager1', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="sync-notification"', html)
        # Le script ne doit plus planter si le conteneur est absent.
        self.assertIn("&& notif)", html)
