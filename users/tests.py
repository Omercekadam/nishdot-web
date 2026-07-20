"""
Kayıt / OTP güvenlik testleri.

En kritik regresyon: e-posta doğrulama bypass'ının (eski form POST'unun)
tekrar açılmadığını garanti eder.
"""
import json

from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterBypassTests(TestCase):
    def test_register_page_get_ok(self):
        resp = self.client.get(reverse("users:register"))
        self.assertEqual(resp.status_code, 200)

    def test_register_form_post_does_not_create_user(self):
        """
        REGRESYON: /auth/register/'a doğrudan form POST'u ATILAMAMALI.
        Eskiden bu, OTP'siz doğrulanmış oturum açıyordu.
        """
        resp = self.client.post(reverse("users:register"), {
            "first_name": "Ali", "last_name": "Veli",
            "email": "bypass@example.com",
            "password": "SuperGizli123", "password_confirm": "SuperGizli123",
        })
        self.assertEqual(resp.status_code, 405)  # Method Not Allowed
        self.assertFalse(User.objects.filter(email="bypass@example.com").exists())
        # Oturum açılmamış olmalı
        self.assertNotIn("_auth_user_id", self.client.session)


@override_settings(RATELIMIT_ENABLE=False)
class OtpApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()  # IP/e-posta kilit durumları testler arası sızmasın

    def _register(self, email="yeni@example.com"):
        return self.client.post(
            reverse("users:api_register"),
            data=json.dumps({
                "email": email, "password": "SuperGizli123",
                "first_name": "Yeni", "last_name": "Uye",
            }),
            content_type="application/json",
        )

    def test_register_creates_unverified_user(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 200)
        user = User.objects.get(email="yeni@example.com")
        self.assertFalse(user.is_verified)
        self.assertTrue(user.verification_code)

    def test_verify_with_wrong_code_fails_and_stays_unverified(self):
        self._register()
        resp = self.client.post(
            reverse("users:api_verify"),
            data=json.dumps({"email": "yeni@example.com", "code": "000000"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(User.objects.get(email="yeni@example.com").is_verified)

    def test_verify_with_correct_code_succeeds(self):
        self._register()
        user = User.objects.get(email="yeni@example.com")
        resp = self.client.post(
            reverse("users:api_verify"),
            data=json.dumps({"email": "yeni@example.com", "code": user.verification_code}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(User.objects.get(email="yeni@example.com").is_verified)

    def test_resend_does_not_leak_account_existence(self):
        """Var olmayan hesap ile resend, var olan ile AYNI yanıtı döndürmeli."""
        r1 = self.client.post(
            reverse("users:api_resend_otp"),
            data=json.dumps({"email": "yok@example.com"}),
            content_type="application/json",
        )
        self._register(email="var@example.com")
        r2 = self.client.post(
            reverse("users:api_resend_otp"),
            data=json.dumps({"email": "var@example.com"}),
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, r2.status_code)
        self.assertEqual(json.loads(r1.content), json.loads(r2.content))

    def test_verify_lockout_after_repeated_failures(self):
        """5 hatalı denemeden sonra 429 (kilit) dönmeli."""
        self._register(email="kilit@example.com")
        last = None
        for _ in range(6):
            last = self.client.post(
                reverse("users:api_verify"),
                data=json.dumps({"email": "kilit@example.com", "code": "111111"}),
                content_type="application/json",
            )
        self.assertEqual(last.status_code, 429)
