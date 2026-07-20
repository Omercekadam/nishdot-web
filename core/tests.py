"""
Kripto yardımcıları ve HTML sanitizasyon filtresi testleri.
"""
from django.test import TestCase
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
