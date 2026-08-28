"""
Herkese açık sayfa, SEO ve iletişim formu testleri.
"""
import json
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from events.models import Event
from pages.models import LegalDocument


class SitemapTests(TestCase):
    """sitemap.xml yalnızca yayında ve tamamlanmış içeriği listelemeli."""

    def setUp(self):
        simdi = timezone.now()
        ortak = {
            "description": "x", "event_type": Event.EventType.WORKSHOP,
            "start_date": simdi, "end_date": simdi + timedelta(hours=2),
            "location": "Kampüs",
        }
        Event.objects.create(title="Yayında", slug="yayinda", status=Event.Status.PUBLISHED, **ortak)
        Event.objects.create(title="Taslak", slug="taslak", status=Event.Status.DRAFT, **ortak)
        LegalDocument.objects.create(title="KVKK", slug="kvkk", content="<p>metin</p>")

    def test_sitemap_lists_published_event(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/events/yayinda/")

    def test_sitemap_hides_draft_event(self):
        """REGRESYON: taslak etkinlik arama motoruna bildirilmemeli."""
        resp = self.client.get("/sitemap.xml")
        self.assertNotContains(resp, "/events/taslak/")

    def test_sitemap_lists_legal_document(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/legal/kvkk/")


class RobotsTxtTests(TestCase):
    def test_robots_disallows_management_paths(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain")
        icerik = resp.content.decode()
        self.assertIn("Disallow: /management/", icerik)
        self.assertIn("Disallow: /yonetim/", icerik)
        self.assertIn("Sitemap: https://nishdot.com.tr/sitemap.xml", icerik)


class LegalDocumentTests(TestCase):
    def test_document_content_is_sanitized(self):
        """REGRESYON: yasal belge içeriği |safe ile değil |sanitize ile basılmalı.

        Not: base.html'in kendi meşru <script> etiketi (çift-gönderim
        engelleme JS'i) var — bu yüzden kaba "<script>" araması yerine
        enjekte edilen payload'a özgü bir belirteç (alert(1)) aranır.
        """
        LegalDocument.objects.create(
            title="Test", slug="test-belge",
            content='<p>güvenli</p><script>alert(1)</script>',
        )
        resp = self.client.get(reverse("pages:legal_document", kwargs={"slug": "test-belge"}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "güvenli")
        self.assertNotContains(resp, "alert(1)")

    def test_missing_document_returns_404(self):
        resp = self.client.get(reverse("pages:legal_document", kwargs={"slug": "yok"}))
        self.assertEqual(resp.status_code, 404)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    RATELIMIT_ENABLE=False,
)
class ContactApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("pages:api_contact")

    def _gonder(self, **extra):
        veri = {
            "full_name": "Test Kişi",
            "email": "test@example.com",
            "subject": "Konu",
            "message": "Mesaj",
        }
        veri.update(extra)
        return self.client.post(self.url, data=json.dumps(veri), content_type="application/json")

    def test_valid_submission_accepted(self):
        resp = self._gonder()
        self.assertEqual(resp.status_code, 200)

    def test_missing_field_rejected(self):
        resp = self._gonder(message="")
        self.assertEqual(resp.status_code, 400)

    def test_invalid_json_rejected(self):
        resp = self.client.post(self.url, data="bu json degil", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_get_not_allowed(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 405)


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        resp = self.client.get(reverse("pages:home"))
        self.assertEqual(resp.status_code, 200)

    def test_draft_event_not_listed_on_home(self):
        simdi = timezone.now()
        Event.objects.create(
            title="Gizli Taslak", slug="gizli-taslak", description="x",
            event_type=Event.EventType.WORKSHOP, status=Event.Status.DRAFT,
            start_date=simdi, end_date=simdi + timedelta(hours=2), location="Kampüs",
        )
        resp = self.client.get(reverse("pages:home"))
        self.assertNotContains(resp, "Gizli Taslak")
