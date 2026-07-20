"""
Sitemap tanımları
=================

Arama motorlarına yayında olan içeriği bildirir. /sitemap.xml adresinden
sunulur (bkz. nishdot/urls.py) ve robots.txt bu adresi işaret eder.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from events.models import Event
from .models import LegalDocument


class StaticViewSitemap(Sitemap):
    """Sabit sayfalar (ana sayfa)."""
    priority = 1.0
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return ["pages:home"]

    def location(self, item):
        return reverse(item)


class EventSitemap(Sitemap):
    """Yayında ve tamamlanmış etkinlikler."""
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        return Event.objects.filter(
            status__in=[Event.Status.PUBLISHED, Event.Status.COMPLETED]
        ).order_by("-start_date")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("events:detail", kwargs={"slug": obj.slug})


class LegalDocumentSitemap(Sitemap):
    """KVKK / yasal belgeler."""
    changefreq = "monthly"
    priority = 0.3
    protocol = "https"

    def items(self):
        return LegalDocument.objects.all()

    def lastmod(self, obj):
        return getattr(obj, "updated_at", None)

    def location(self, obj):
        return reverse("pages:legal_document", kwargs={"slug": obj.slug})


SITEMAPS = {
    "static": StaticViewSitemap,
    "events": EventSitemap,
    "legal": LegalDocumentSitemap,
}
