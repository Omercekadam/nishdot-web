"""
Kripto yardımcıları ve HTML sanitizasyon filtresi testleri.
"""
from django.test import TestCase, override_settings
from django.template import Context, Template

from core.crypto import (
    encrypt_value, decrypt_value, hash_national_id,
    is_encrypted, is_valid_national_id,
)


class CryptoTests(TestCase):
    def test_encrypt_roundtrip(self):
        token = encrypt_value("12345678950")
        self.assertTrue(is_encrypted(token))
        self.assertNotIn("12345678950", token)
        self.assertEqual(decrypt_value(token), "12345678950")

    def test_hash_is_deterministic_and_not_plain_sha(self):
        h1 = hash_national_id("12345678950")
        h2 = hash_national_id("12345678950")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)
        # Tuzsuz SHA-256 ile aynı OLMAMALI (HMAC kullanılıyor)
        import hashlib
        self.assertNotEqual(h1, hashlib.sha256(b"12345678950").hexdigest())

    def test_national_id_validation(self):
        self.assertTrue(is_valid_national_id("12345678950"))
        self.assertFalse(is_valid_national_id("123"))
        self.assertFalse(is_valid_national_id("01234567890"))  # 0 ile başlar
        self.assertFalse(is_valid_national_id("1234567895a"))
        self.assertFalse(is_valid_national_id(""))


class SanitizeFilterTests(TestCase):
    def _render(self, raw):
        tpl = Template("{% load sanitize %}{{ raw|sanitize }}")
        return tpl.render(Context({"raw": raw}))

    def test_strips_script_and_handlers(self):
        out = self._render('<p>ok</p><script>alert(1)</script>'
                           '<a href="javascript:alert(2)" onclick="x()">l</a>'
                           '<img src=x onerror=alert(3)>')
        self.assertNotIn("<script>", out)
        self.assertNotIn("onerror", out)
        self.assertNotIn("onclick", out)
        self.assertNotIn("javascript:", out)

    def test_keeps_safe_markup(self):
        out = self._render("<p>Merhaba</p><strong>kalın</strong><h2>Başlık</h2><ul><li>a</li></ul>")
        self.assertIn("<p>", out)
        self.assertIn("<strong>", out)
        self.assertIn("<h2>", out)
        self.assertIn("<li>", out)


class ClientIpTests(TestCase):
    """SecurityLog, rate limit ile AYNI IP kaynağını kullanmalı."""

    def setUp(self):
        from django.test import RequestFactory
        self.factory = RequestFactory()

    def _istek(self, **meta):
        from core.http import get_client_ip
        request = self.factory.get("/")
        request.META.update(meta)
        return get_client_ip(request)

    @override_settings(RATELIMIT_IP_META_KEY="HTTP_X_REAL_IP")
    def test_prefers_configured_meta_key(self):
        """Production'da proxy'nin IP'si değil, X-Real-IP okunmalı."""
        ip = self._istek(HTTP_X_REAL_IP="203.0.113.7", REMOTE_ADDR="127.0.0.1")
        self.assertEqual(ip, "203.0.113.7")

    @override_settings(RATELIMIT_IP_META_KEY="HTTP_X_REAL_IP")
    def test_falls_back_to_remote_addr_when_header_missing(self):
        ip = self._istek(REMOTE_ADDR="198.51.100.4")
        self.assertEqual(ip, "198.51.100.4")

    def test_uses_remote_addr_when_no_meta_key_configured(self):
        """Development'ta RATELIMIT_IP_META_KEY tanımlı değil."""
        ip = self._istek(REMOTE_ADDR="198.51.100.9")
        self.assertEqual(ip, "198.51.100.9")

    def test_never_returns_empty_string(self):
        """GenericIPAddressField boş string kabul etmez (PostgreSQL inet)."""
        from core.http import FALLBACK_IP
        self.assertEqual(self._istek(REMOTE_ADDR=""), FALLBACK_IP)

    @override_settings(RATELIMIT_IP_META_KEY="HTTP_X_FORWARDED_FOR")
    def test_takes_first_address_from_comma_list(self):
        """X-Forwarded-For virgüllü liste olabilir; ilki gerçek istemcidir."""
        ip = self._istek(HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1", REMOTE_ADDR="10.0.0.1")
        self.assertEqual(ip, "203.0.113.7")
